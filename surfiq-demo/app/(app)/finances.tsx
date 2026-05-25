import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Platform,
} from 'react-native'
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import {
  format, startOfWeek, endOfWeek, startOfMonth, endOfMonth,
  subDays, subWeeks, subMonths, addDays,
} from 'date-fns'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import { C } from '@/constants/Colors'
import { trackPageView, trackFeature } from '@/lib/analytics'
import { useLang, getCurrencySymbol, fmtCurrency, fmtPerHour } from '@/lib/i18n'

// ─── Types ──────────────────────────────────────────────────────────────

type PeriodKey = 'today' | 'week' | 'month' | 'season2026' | 'season2025' | 'all'

const PERIOD_LABELS: Record<PeriodKey, string> = {
  today: 'Dziś',
  week: 'Tydzień',
  month: 'Miesiąc',
  season2026: 'Sezon 2026',
  season2025: 'Sezon 2025',
  all: 'Wszystko',
}

const EUR_RATE = 4.3

// ─── Date range helpers ─────────────────────────────────────────────────

function getPeriodRange(key: PeriodKey): { from: string; to: string; season: 'current' | '2025' | 'all' } {
  const now = new Date()
  switch (key) {
    case 'today':
      return { from: format(now, 'yyyy-MM-dd'), to: format(now, 'yyyy-MM-dd'), season: 'current' }
    case 'week':
      return { from: format(startOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd'), to: format(endOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd'), season: 'current' }
    case 'month':
      return { from: format(startOfMonth(now), 'yyyy-MM-dd'), to: format(endOfMonth(now), 'yyyy-MM-dd'), season: 'current' }
    case 'season2026':
      return { from: '2026-04-01', to: '2026-10-31', season: 'current' }
    case 'season2025':
      return { from: '2025-05-01', to: '2025-09-30', season: '2025' }
    case 'all':
      return { from: '2020-01-01', to: '2030-12-31', season: 'all' }
  }
}

function getPrevPeriodRange(key: PeriodKey): { from: string; to: string; season: 'current' | '2025' | 'all' } | null {
  const now = new Date()
  switch (key) {
    case 'today': {
      const y = subDays(now, 1)
      return { from: format(y, 'yyyy-MM-dd'), to: format(y, 'yyyy-MM-dd'), season: 'current' }
    }
    case 'week': {
      const ws = subWeeks(startOfWeek(now, { weekStartsOn: 1 }), 1)
      return { from: format(ws, 'yyyy-MM-dd'), to: format(addDays(ws, 6), 'yyyy-MM-dd'), season: 'current' }
    }
    case 'month': {
      const ms = subMonths(startOfMonth(now), 1)
      return { from: format(ms, 'yyyy-MM-dd'), to: format(endOfMonth(ms), 'yyyy-MM-dd'), season: 'current' }
    }
    case 'season2026':
      return { from: '2025-05-01', to: '2025-09-30', season: '2025' }
    case 'season2025':
      return null // no previous season data
    case 'all':
      return null
  }
}

// ─── Apply season channel filter ────────────────────────────────────────

function applySeasonFilter(q: any, season: 'current' | '2025' | 'all') {
  if (season === 'current') {
    q = q.or('external_channel.is.null,external_channel.neq.legacy_import')
  } else if (season === '2025') {
    q = q.eq('external_channel', 'legacy_import')
  }
  // 'all' — no filter
  return q
}

// ─── Data fetcher ───────────────────────────────────────────────────────

async function fetchFinanceData(location: string, period: PeriodKey) {
  const range = getPeriodRange(period)
  const prevRange = getPrevPeriodRange(period)
  const locFilter = location !== 'both' ? location : null

  // Build base query for a date range
  const buildQ = (dateFrom: string, dateTo: string, season: 'current' | '2025' | 'all', paymentFilter?: string) => {
    let q = supabase
      .from('bookings')
      .select('total_price, currency, service_name_snap, payment_status, booking_status, duration_hours, start_time, end_time, instructor_snap')
      .gte('start_date', dateFrom)
      .lte('start_date', dateTo)
      .neq('booking_status', 'cancelled')
    q = applySeasonFilter(q, season)
    if (locFilter) q = q.eq('location', locFilter)
    if (paymentFilter) q = q.eq('payment_status', paymentFilter)
    return q
  }

  // Current + previous period — parallel queries
  const queries: Promise<any>[] = [
    buildQ(range.from, range.to, range.season),
    buildQ(range.from, range.to, range.season, 'paid'),
  ]
  if (prevRange) {
    queries.push(buildQ(prevRange.from, prevRange.to, prevRange.season, 'paid'))
    queries.push(buildQ(prevRange.from, prevRange.to, prevRange.season))
  }
  const results = await Promise.all(queries)
  const { data: periodAll } = results[0]
  const { data: periodPaid } = results[1]
  let prevPaid: any[] | null = prevRange ? results[2]?.data : null
  let prevAll: any[] | null = prevRange ? results[3]?.data : null

  // Unpaid bookings (always current season scope, not date-filtered)
  let unpaidQ = supabase
    .from('bookings')
    .select('id, booking_ref, customer_name, service_name_snap, start_date, total_price, currency, payment_status')
    .in('payment_status', ['unpaid', 'deposit_paid'])
    .neq('booking_status', 'cancelled')
    .gte('start_date', range.from)
    .lte('start_date', range.to)
    .order('start_date', { ascending: true })
    .limit(30)
  unpaidQ = applySeasonFilter(unpaidQ, range.season)
  if (locFilter) unpaidQ = unpaidQ.eq('location', locFilter)
  const { data: unpaidBookings } = await unpaidQ

  // Revenue by service (paid bookings in period)
  const serviceRevenue: Record<string, { pln: number; eur: number; count: number }> = {}
  ;(periodPaid ?? []).forEach((b: any) => {
    const name = b.service_name_snap || 'Inne'
    if (!serviceRevenue[name]) serviceRevenue[name] = { pln: 0, eur: 0, count: 0 }
    serviceRevenue[name].count++
    if (b.currency === 'PLN') serviceRevenue[name].pln += Number(b.total_price || 0)
    else serviceRevenue[name].eur += Number(b.total_price || 0)
  })

  // Instructor rates for cost calc
  const { data: instrRates } = await supabase.from('instructors').select('first_name, last_name, hourly_rate')
  const rateMap: Record<string, number> = {}
  for (const i of instrRates ?? []) {
    rateMap[`${i.first_name} ${i.last_name}`.trim()] = Number(i.hourly_rate) || 0
  }

  // Hours & cost calculation for period
  let hoursQ = supabase
    .from('bookings')
    .select('instructor_snap, duration_hours, start_time, end_time, service_name_snap, total_price, currency')
    .gte('start_date', range.from)
    .lte('start_date', range.to)
    .neq('booking_status', 'cancelled')
  hoursQ = applySeasonFilter(hoursQ, range.season)
  if (locFilter) hoursQ = hoursQ.eq('location', locFilter)
  const { data: hoursData } = await hoursQ

  let totalInstrCost = 0
  let totalRevenueHours = 0
  for (const b of hoursData ?? []) {
    let h = Number(b.duration_hours) || 0
    if (!h && b.start_time && b.end_time) {
      const [sh, sm] = b.start_time.split(':').map(Number)
      const [eh, em] = b.end_time.split(':').map(Number)
      h = Math.max(0, (eh * 60 + em - sh * 60 - sm) / 60)
    }
    totalRevenueHours += h
    const rate = rateMap[b.instructor_snap ?? ''] ?? 0
    if (rate > 0) {
      const isGroup = (b.service_name_snap ?? '').toLowerCase().includes('grupow') || (b.service_name_snap ?? '').toLowerCase().includes('podwójn')
      totalInstrCost += h * (isGroup ? Math.round(rate * 1.15) : rate)
    }
  }

  const sumPLN = (arr: any[] | null) => (arr ?? []).filter(b => b.currency === 'PLN').reduce((s: number, b: any) => s + Number(b.total_price || 0), 0)
  const sumEUR = (arr: any[] | null) => (arr ?? []).filter(b => b.currency === 'EUR').reduce((s: number, b: any) => s + Number(b.total_price || 0), 0)
  const toEquivPLN = (pln: number, eur: number) => pln + eur * EUR_RATE

  const periodRevPLN = sumPLN(periodPaid)
  const periodRevEUR = sumEUR(periodPaid)
  const periodRevTotal = toEquivPLN(periodRevPLN, periodRevEUR)

  const allRevPLN = sumPLN(periodAll)
  const allRevEUR = sumEUR(periodAll)

  const unpaidPLN = sumPLN(unpaidBookings)
  const unpaidEUR = sumEUR(unpaidBookings)

  // Previous period revenue for delta
  const prevRevTotal = prevPaid ? toEquivPLN(sumPLN(prevPaid), sumEUR(prevPaid)) : null
  const prevBookingCount = prevAll ? (prevAll ?? []).length : null

  // Delta percentages
  const revenueDelta = prevRevTotal != null && prevRevTotal > 0
    ? Math.round(((periodRevTotal - prevRevTotal) / prevRevTotal) * 100)
    : null
  const bookingsDelta = prevBookingCount != null && prevBookingCount > 0
    ? Math.round((((periodAll ?? []).length - prevBookingCount) / prevBookingCount) * 100)
    : null

  const costPerHour = totalRevenueHours > 0 ? Math.round(totalInstrCost / totalRevenueHours) : 0
  const revenuePerHour = totalRevenueHours > 0 ? Math.round(periodRevTotal / totalRevenueHours) : 0
  const profitPerHour = revenuePerHour - costPerHour

  return {
    paidPLN: periodRevPLN,
    paidEUR: periodRevEUR,
    allPLN: allRevPLN,
    allEUR: allRevEUR,
    bookingCount: (periodAll ?? []).length,
    paidCount: (periodPaid ?? []).length,
    totalRevenueHours: Math.round(totalRevenueHours * 10) / 10,
    costPerHour,
    revenuePerHour,
    profitPerHour,
    totalInstrCost,
    unpaidPLN,
    unpaidEUR,
    unpaidBookings: unpaidBookings ?? [],
    serviceRevenue: Object.entries(serviceRevenue).sort((a, b) => (b[1].pln + b[1].eur * EUR_RATE) - (a[1].pln + a[1].eur * EUR_RATE)),
    revenueDelta,
    bookingsDelta,
    prevRevTotal,
  }
}

// ─── Helpers ────────────────────────────────────────────────────────────

function fmtMoney(pln: number, eur: number): string {
  const parts: string[] = []
  if (pln > 0) parts.push(`${pln.toLocaleString('pl-PL')} PLN`)
  if (eur > 0) parts.push(`${eur.toLocaleString('pl-PL')} EUR`)
  return parts.join(' + ') || '0 PLN'
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta == null) return null
  const isUp = delta >= 0
  return (
    <View style={[s.deltaBadge, { backgroundColor: isUp ? C.success + '18' : C.error + '18' }]}>
      <Ionicons name={isUp ? 'trending-up' : 'trending-down'} size={12} color={isUp ? C.success : C.error} />
      <Text style={[s.deltaText, { color: isUp ? C.success : C.error }]}>
        {isUp ? '+' : ''}{delta}%
      </Text>
    </View>
  )
}

function getPeriodSubtitle(period: PeriodKey): string {
  const now = new Date()
  switch (period) {
    case 'today': return format(now, 'dd.MM.yyyy')
    case 'week': return `${format(startOfWeek(now, { weekStartsOn: 1 }), 'dd.MM')} - ${format(endOfWeek(now, { weekStartsOn: 1 }), 'dd.MM.yyyy')}`
    case 'month': return format(now, 'LLLL yyyy')
    case 'season2026': return 'kwiecień - październik 2026'
    case 'season2025': return 'maj - wrzesień 2025 (archiwum)'
    case 'all': return 'cały okres'
  }
}

function getDeltaLabel(period: PeriodKey): string {
  switch (period) {
    case 'today': return 'vs wczoraj'
    case 'week': return 'vs zeszły tydzień'
    case 'month': return 'vs zeszły miesiąc'
    case 'season2026': return 'vs sezon 2025'
    case 'season2025': return ''
    case 'all': return ''
  }
}

// ─── Component ──────────────────────────────────────────────────────────

export default function FinancesScreen() {
  const { selectedLocation } = useAuth()
  const router = useRouter()
  const [period, setPeriod] = useState<PeriodKey>('month')
  const { t } = useLang()

  useEffect(() => { trackPageView('finances') }, [])

  const { data, isLoading } = useQuery({
    queryKey: ['finances', selectedLocation, period],
    queryFn: () => fetchFinanceData(selectedLocation, period),
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
  })

  const handlePeriodChange = (key: PeriodKey) => {
    setPeriod(key)
    trackFeature('finance_period', { period: key })
  }

  return (
    <View style={s.root}>
      {/* Header */}
      <View style={s.header}>
        <Text style={s.headerTitle}>{t('fin.title')}</Text>
        <Text style={s.headerSub}>{getPeriodSubtitle(period)}</Text>
      </View>

      {/* Period chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={s.chipRow}
        style={s.chipScroll}
      >
        {(Object.keys(PERIOD_LABELS) as PeriodKey[]).map(k => (
          <TouchableOpacity
            key={k}
            style={[s.chip, period === k && s.chipActive]}
            onPress={() => handlePeriodChange(k)}
            activeOpacity={0.7}
          >
            <Text style={[s.chipText, period === k && s.chipTextActive]}>{PERIOD_LABELS[k]}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView style={s.scroll} contentContainerStyle={s.scrollContent} showsVerticalScrollIndicator={true}>
        {isLoading ? (
          <ActivityIndicator color={C.primary} size="large" style={{ marginTop: 60 }} />
        ) : data ? (
          <>
            {/* ── Main revenue card ──────────────────────── */}
            <View style={s.mainCard}>
              <View style={s.mainCardHeader}>
                <Text style={s.mainCardLabel}>{t('fin.revenue_paid')}</Text>
                <DeltaBadge delta={data.revenueDelta} />
              </View>
              <Text style={s.mainCardValue}>{fmtMoney(data.paidPLN, data.paidEUR)}</Text>
              {data.allPLN + data.allEUR > data.paidPLN + data.paidEUR && (
                <Text style={s.mainCardSub}>Wszystkie: {fmtMoney(data.allPLN, data.allEUR)}</Text>
              )}
              {data.revenueDelta != null && getDeltaLabel(period) !== '' && (
                <Text style={s.mainCardDeltaLabel}>{getDeltaLabel(period)}</Text>
              )}
            </View>

            {/* ── Stats grid (2x2) ───────────────────────── */}
            <View style={s.periodGrid}>
              <View style={s.periodCard}>
                <View style={s.periodLabelRow}>
                  <Ionicons name="calendar-outline" size={13} color={C.primary} />
                  <Text style={s.periodLabel}>{t('fin.bookings')}</Text>
                </View>
                <View style={s.periodValueRow}>
                  <Text style={[s.periodValue, { color: C.primary }]}>{data.bookingCount}</Text>
                  <DeltaBadge delta={data.bookingsDelta} />
                </View>
                <Text style={s.periodSub}>{data.paidCount} {t('fin.paid_count')}</Text>
              </View>
              <View style={s.periodCard}>
                <View style={s.periodLabelRow}>
                  <Ionicons name="time-outline" size={13} color={C.accent} />
                  <Text style={s.periodLabel}>{t('fin.hours')}</Text>
                </View>
                <Text style={[s.periodValue, { color: C.accent }]}>{data.totalRevenueHours}h</Text>
                <Text style={s.periodSub}>{t('fin.instructor_work')}</Text>
              </View>
              <View style={s.periodCard}>
                <View style={s.periodLabelRow}>
                  <Ionicons name="cash-outline" size={13} color={C.warning} />
                  <Text style={s.periodLabel}>{t('fin.cost_per_hour')}</Text>
                </View>
                <Text style={[s.periodValue, { color: C.warning }]}>{data.costPerHour} {getCurrencySymbol()}</Text>
                <Text style={s.periodSub}>{t('fin.instructor_rate')}</Text>
              </View>
              <View style={[s.periodCard, { borderColor: data.unpaidPLN + data.unpaidEUR > 0 ? C.error + '60' : C.border }]}>
                <View style={s.periodLabelRow}>
                  <Ionicons name="alert-circle-outline" size={13} color={data.unpaidPLN + data.unpaidEUR > 0 ? C.error : C.success} />
                  <Text style={s.periodLabel}>{t('fin.arrears')}</Text>
                </View>
                <Text style={[s.periodValue, { color: data.unpaidPLN + data.unpaidEUR > 0 ? C.error : C.success }]}>
                  {data.unpaidPLN + data.unpaidEUR > 0 ? fmtMoney(data.unpaidPLN, data.unpaidEUR) : t('fin.no_arrears')}
                </Text>
                <Text style={s.periodSub}>{data.unpaidBookings.length} {t('fin.bookings').toLowerCase()}</Text>
              </View>
            </View>

            {/* ── Cost breakdown ──────────────────────────── */}
            <Text style={s.sectionTitle}>{t('fin.labor_costs')}</Text>
            <View style={s.periodGrid}>
              <View style={s.periodCard}>
                <View style={s.periodLabelRow}>
                  <Ionicons name="trending-up-outline" size={13} color={C.success} />
                  <Text style={s.periodLabel}>{t('fin.revenue_per_hour')}</Text>
                </View>
                <Text style={[s.periodValue, { color: C.success }]}>{data.revenuePerHour} {getCurrencySymbol()}</Text>
                <Text style={s.periodSub}>{data.totalRevenueHours}h</Text>
              </View>
              <View style={s.periodCard}>
                <View style={s.periodLabelRow}>
                  <Ionicons name="wallet-outline" size={13} color={data.profitPerHour > 0 ? C.success : C.error} />
                  <Text style={s.periodLabel}>{t('fin.profit_per_hour')}</Text>
                </View>
                <Text style={[s.periodValue, { color: data.profitPerHour > 0 ? C.success : C.error }]}>{data.profitPerHour} {getCurrencySymbol()}</Text>
                <Text style={s.periodSub}>{t('fin.after_instructor')}</Text>
              </View>
              <View style={s.periodCard}>
                <View style={s.periodLabelRow}>
                  <Ionicons name="people-outline" size={13} color={C.error} />
                  <Text style={s.periodLabel}>{t('fin.instructor_cost')}</Text>
                </View>
                <Text style={[s.periodValue, { color: C.error }]}>{data.totalInstrCost.toLocaleString('pl-PL')} {getCurrencySymbol()}</Text>
                <Text style={s.periodSub}>{t('fin.total_cost')}</Text>
              </View>
              <View style={s.periodCard}>
                <View style={s.periodLabelRow}>
                  <Ionicons name="cash-outline" size={13} color={C.warning} />
                  <Text style={s.periodLabel}>{t('fin.cost_per_hour')}</Text>
                </View>
                <Text style={[s.periodValue, { color: C.warning }]}>{data.costPerHour} {getCurrencySymbol()}</Text>
                <Text style={s.periodSub}>{t('fin.instructor_rate')}</Text>
              </View>
            </View>

            {/* ── Revenue by service ──────────────────────── */}
            {data.serviceRevenue.length > 0 && (
              <>
                <Text style={s.sectionTitle}>{t('fin.revenue_by_service')}</Text>
                {data.serviceRevenue.map(([name, rev]) => (
                  <View key={name} style={s.serviceRow}>
                    <View style={s.serviceLeft}>
                      <Text style={s.serviceName}>{name}</Text>
                      <Text style={s.serviceCount}>{rev.count} rezerwacji</Text>
                    </View>
                    <Text style={s.serviceAmount}>{fmtMoney(rev.pln, rev.eur)}</Text>
                  </View>
                ))}
              </>
            )}

            {/* ── Unpaid bookings ─────────────────────────── */}
            {data.unpaidBookings.length > 0 && (
              <>
                <View style={s.sectionRow}>
                  <Text style={s.sectionTitle}>{t('fin.unpaid_bookings')}</Text>
                  <View style={s.badgeError}>
                    <Text style={s.badgeErrorText}>{data.unpaidBookings.length}</Text>
                  </View>
                </View>
                {data.unpaidBookings.map((b: any) => (
                  <TouchableOpacity
                    key={b.id}
                    style={s.unpaidCard}
                    onPress={() => router.push(`/(app)/bookings/${b.id}` as any)}
                    activeOpacity={0.75}
                  >
                    <View style={s.unpaidLeft}>
                      <Text style={s.unpaidName}>{b.customer_name}</Text>
                      <Text style={s.unpaidService}>{b.service_name_snap}</Text>
                      <Text style={s.unpaidDate}>{b.start_date} · {b.booking_ref}</Text>
                    </View>
                    <View style={s.unpaidRight}>
                      <Text style={s.unpaidPrice}>{b.total_price} {b.currency}</Text>
                      <View style={[s.unpaidBadge, { backgroundColor: b.payment_status === 'unpaid' ? C.error + '22' : C.warning + '22' }]}>
                        <Text style={[s.unpaidBadgeText, { color: b.payment_status === 'unpaid' ? C.error : C.warning }]}>
                          {b.payment_status === 'unpaid' ? t('fin.unpaid') : t('fin.deposit')}
                        </Text>
                      </View>
                    </View>
                  </TouchableOpacity>
                ))}
              </>
            )}

            {/* ── Quick links ───────────────────────────── */}
            <Text style={s.sectionTitle}>{t('fin.more_analysis')}</Text>
            <View style={{ gap: 8, marginBottom: 40 }}>
              <TouchableOpacity style={s.linkCard} onPress={() => router.push('/(app)/more/reports' as any)} activeOpacity={0.7}>
                <Text style={{ fontSize: 22 }}>📊</Text>
                <View style={{ flex: 1 }}>
                  <Text style={s.linkTitle}>Raporty wizualne</Text>
                  <Text style={s.linkSub}>Wykresy, rentownosc, porownania · 2025 + 2026</Text>
                </View>
                <Ionicons name="chevron-forward" size={16} color={C.border} />
              </TouchableOpacity>
              <TouchableOpacity style={s.linkCard} onPress={() => router.push('/(app)/more/analytics' as any)} activeOpacity={0.7}>
                <Text style={{ fontSize: 22 }}>📈</Text>
                <View style={{ flex: 1 }}>
                  <Text style={s.linkTitle}>Dane & CSV export</Text>
                  <Text style={s.linkSub}>Tabele, filtry, eksport · 2025 + 2026</Text>
                </View>
                <Ionicons name="chevron-forward" size={16} color={C.border} />
              </TouchableOpacity>
              <TouchableOpacity style={s.linkCard} onPress={() => router.push('/(app)/more/hr' as any)} activeOpacity={0.7}>
                <Text style={{ fontSize: 22 }}>👨‍🏫</Text>
                <View style={{ flex: 1 }}>
                  <Text style={s.linkTitle}>HR & Wynagrodzenia</Text>
                  <Text style={s.linkSub}>Godziny pracy, stawki, wyplaty</Text>
                </View>
                <Ionicons name="chevron-forward" size={16} color={C.border} />
              </TouchableOpacity>
            </View>
          </>
        ) : null}
      </ScrollView>
    </View>
  )
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: {
    backgroundColor: C.surface,
    paddingTop: Platform.OS === 'web' ? 24 : 56,
    paddingBottom: 12, paddingHorizontal: 20,
    borderBottomWidth: 0,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  headerTitle: { color: C.text, fontSize: 22, fontWeight: '800' },
  headerSub: { color: C.textMuted, fontSize: 13, marginTop: 2, textTransform: 'capitalize' },

  // Chips
  chipScroll: { backgroundColor: C.surface, borderBottomWidth: 1, borderBottomColor: C.border, maxHeight: 44 },
  chipRow: {
    flexDirection: 'row', flexWrap: 'nowrap', gap: 6, paddingHorizontal: 14,
    paddingVertical: 6, alignItems: 'center',
  },
  chip: {
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12,
    backgroundColor: C.surfaceHigh, borderWidth: 1, borderColor: C.border,
  },
  chipActive: { backgroundColor: C.primary + '18', borderColor: C.primary },
  chipText: { color: C.textMuted, fontSize: 11, fontWeight: '700' },
  chipTextActive: { color: C.primary },

  scroll: { flex: 1 },
  scrollContent: { padding: 14, maxWidth: '100%', overflow: 'hidden' as const },

  sectionTitle: { color: C.text, fontSize: 14, fontWeight: '700', marginBottom: 8, marginTop: 4 },
  sectionRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, marginTop: 4 },

  // Main revenue card
  mainCard: {
    backgroundColor: C.surface, borderRadius: 10, padding: 10, marginBottom: 10,
    borderWidth: 1, borderColor: C.border, borderTopWidth: 3, borderTopColor: C.primary,
  },
  mainCardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  mainCardLabel: { color: C.textMuted, fontSize: 11, fontWeight: '600' },
  mainCardValue: { fontSize: 18, fontWeight: '800', color: C.success, marginBottom: 1 },
  mainCardSub: { color: C.textSec, fontSize: 12, marginBottom: 0 },
  mainCardDeltaLabel: { color: C.textMuted, fontSize: 11, marginTop: 2 },

  // Delta badge
  deltaBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10,
  },
  deltaText: { fontSize: 11, fontWeight: '700' },

  // Period grid
  periodGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 5, marginBottom: 10, maxWidth: '100%' },
  periodCard: {
    flexBasis: '48%' as any, flexGrow: 0, flexShrink: 1,
    backgroundColor: C.surface, borderRadius: 8, paddingVertical: 5, paddingHorizontal: 8,
    borderWidth: 1, borderColor: C.border, overflow: 'hidden' as const,
  },
  periodLabelRow: { flexDirection: 'row', alignItems: 'center', gap: 3, marginBottom: 1 },
  periodLabel: { color: C.textMuted, fontSize: 11, fontWeight: '600' },
  periodValue: { fontSize: 14, fontWeight: '800', marginBottom: 0 },
  periodValueRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  periodSub: { color: C.textMuted, fontSize: 10 },

  // Service breakdown
  serviceRow: {
    backgroundColor: C.surface, borderRadius: 8, padding: 8, marginBottom: 5,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    borderWidth: 1, borderColor: C.border, overflow: 'hidden' as const,
  },
  serviceLeft: { flex: 1 },
  serviceName: { color: C.text, fontSize: 13, fontWeight: '600', marginBottom: 1 },
  serviceCount: { color: C.textMuted, fontSize: 12 },
  serviceAmount: { color: C.success, fontSize: 14, fontWeight: '800' },

  // Unpaid
  unpaidCard: {
    backgroundColor: C.surface, borderRadius: 8, marginBottom: 5,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 8, borderWidth: 1, borderColor: C.error + '40',
    borderLeftWidth: 3, borderLeftColor: C.error, overflow: 'hidden' as const,
  },
  unpaidLeft: { flex: 1 },
  unpaidName: { color: C.text, fontSize: 13, fontWeight: '700', marginBottom: 1 },
  unpaidService: { color: C.textSec, fontSize: 12, marginBottom: 1 },
  unpaidDate: { color: C.textMuted, fontSize: 11 },
  unpaidRight: { alignItems: 'flex-end' },
  unpaidPrice: { color: C.text, fontSize: 14, fontWeight: '700', marginBottom: 3 },
  unpaidBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  unpaidBadgeText: { fontSize: 12, fontWeight: '700' },
  badgeError: { backgroundColor: C.errorSoft, paddingHorizontal: 10, paddingVertical: 3, borderRadius: 10, marginBottom: 12, borderWidth: 1, borderColor: C.error + '40' },
  badgeErrorText: { color: C.error, fontSize: 12, fontWeight: '700' },

  // Links
  linkCard: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: C.surface, borderRadius: 10, padding: 10,
    borderWidth: 1, borderColor: C.border,
  },
  linkTitle: { color: C.text, fontSize: 14, fontWeight: '700' },
  linkSub: { color: C.textMuted, fontSize: 11, marginTop: 2 },
})
