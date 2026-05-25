import { isOwnerEmail } from '@/lib/owner'
import {
  ActivityIndicator, Platform, ScrollView, StyleSheet,
  Text, TouchableOpacity, View,
} from 'react-native'
import { useState, useMemo } from 'react'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useQuery } from '@tanstack/react-query'
import {
  format, startOfWeek, endOfWeek, startOfMonth, endOfMonth,
  subDays, subWeeks, subMonths, differenceInDays, addDays, parseISO,
} from 'date-fns'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import { C } from '@/constants/Colors'
import { BarChart, type BarDatum } from '@/components/charts/BarChart'
import { LineChart, type LineDatum } from '@/components/charts/LineChart'
import { generateReport } from '@/lib/report-generator'
import { fmtCurrency, fmtPerHour, getCurrencySymbol, getCurrency, EUR_RATE as I18N_EUR_RATE } from '@/lib/i18n'

// ─── Owner guard ─────────────────────────────────────────────────────────


// ─── Types ───────────────────────────────────────────────────────────────

type RangeKey = 'today' | 'week' | 'month' | 'season2026' | 'season2025' | 'alltime'

interface RawBooking {
  total_price: number
  currency: string
  payment_status: string
  booking_status: string
  service_name_snap: string
  instructor_snap: string | null
  duration_hours: number | null
  start_time: string | null
  end_time: string | null
  start_date: string
  persons: number
}

const EUR_RATE = 4.3

const SPORT_KEYWORDS = ['Kite', 'Wind', 'Wing', 'SUP', 'Surf', 'Deskorolka', 'Wake', 'Pumpfoil']

function extractSport(name: string): string {
  const lower = name.toLowerCase()
  for (const kw of SPORT_KEYWORDS) {
    if (lower.includes(kw.toLowerCase())) return kw
  }
  return 'Inne'
}

const RANGE_LABELS: Record<RangeKey, string> = {
  today: 'Dziś',
  week: 'Tydzień',
  month: 'Miesiąc',
  season2026: '2026',
  season2025: '2025',
  alltime: 'Wszystko',
}

// ─── Helpers ─────────────────────────────────────────────────────────────

function getRange(key: RangeKey) {
  const now = new Date()
  switch (key) {
    case 'today': return { from: format(now, 'yyyy-MM-dd'), to: format(now, 'yyyy-MM-dd'), season: 'current' as const }
    case 'week': return { from: format(startOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd'), to: format(endOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd'), season: 'current' as const }
    case 'month': return { from: format(startOfMonth(now), 'yyyy-MM-dd'), to: format(endOfMonth(now), 'yyyy-MM-dd'), season: 'current' as const }
    case 'season2026': return { from: '2026-04-01', to: '2026-10-31', season: 'current' as const }
    case 'season2025': return { from: '2025-05-01', to: '2025-09-30', season: '2025' as const }
    case 'alltime': return { from: '2020-01-01', to: '2030-12-31', season: 'all' as const }
  }
}

function getPrevRange(key: RangeKey) {
  const now = new Date()
  switch (key) {
    case 'today': { const y = subDays(now, 1); return { from: format(y, 'yyyy-MM-dd'), to: format(y, 'yyyy-MM-dd'), season: 'current' as const } }
    case 'week': { const ws = subWeeks(startOfWeek(now, { weekStartsOn: 1 }), 1); return { from: format(ws, 'yyyy-MM-dd'), to: format(addDays(ws, 6), 'yyyy-MM-dd'), season: 'current' as const } }
    case 'month': { const ms = subMonths(startOfMonth(now), 1); return { from: format(ms, 'yyyy-MM-dd'), to: format(endOfMonth(ms), 'yyyy-MM-dd'), season: 'current' as const } }
    case 'season2026': return { from: '2025-04-01', to: '2025-10-31', season: '2025' as const }
    case 'season2025': return { from: '2024-04-01', to: '2024-10-31', season: 'all' as const }
    case 'alltime': return { from: '2020-01-01', to: '2030-12-31', season: 'all' as const }
  }
}

function getDurationH(b: RawBooking): number {
  if (b.duration_hours != null && b.duration_hours > 0) return b.duration_hours
  if (b.start_time && b.end_time) {
    const [sh, sm] = b.start_time.split(':').map(Number)
    const [eh, em] = b.end_time.split(':').map(Number)
    const diff = (eh * 60 + em - sh * 60 - sm) / 60
    return diff > 0 ? diff : 0
  }
  return 0
}

function isBosman(serviceName: string): boolean {
  return serviceName.toLowerCase().includes('bosman') || serviceName.toLowerCase().includes('bosun')
}

function toPLN(price: number, currency: string): number {
  return currency === 'EUR' ? price * EUR_RATE : price
}

function fmtMoney(v: number): string {
  return fmtCurrency(v, { short: true })
}

function fmtRate(v: number): string {
  return fmtPerHour(v)
}

function delta(curr: number, prev: number): { pct: number; label: string; positive: boolean } | null {
  if (prev === 0 && curr === 0) return null
  if (prev === 0) return { pct: 100, label: '+100%', positive: true }
  const pct = ((curr - prev) / prev) * 100
  return { pct, label: `${pct >= 0 ? '+' : ''}${Math.round(pct)}%`, positive: pct >= 0 }
}

// ─── Data fetch ──────────────────────────────────────────────────────────

async function fetchBookings(from: string, to: string, location: string, seasonFilter?: string) {
  const all: RawBooking[] = []
  let page = 0
  const PAGE_SIZE = 1000
  while (true) {
    let q = supabase
      .from('bookings')
      .select('total_price, currency, payment_status, booking_status, service_name_snap, instructor_snap, duration_hours, start_time, end_time, start_date, persons')
      .gte('start_date', from)
      .lte('start_date', to)
      .neq('booking_status', 'cancelled')
      .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1)

    if (seasonFilter === '2025') {
      q = q.eq('external_channel', 'legacy_import')
    } else if (seasonFilter === 'all') {
      // no filter — get everything
    } else {
      q = q.or('external_channel.is.null,external_channel.neq.legacy_import')
    }

    if (location !== 'both') q = q.eq('location', location)

    const { data } = await q
    if (!data || data.length === 0) break
    all.push(...(data as RawBooking[]))
    if (data.length < PAGE_SIZE) break
    page++
  }
  return all
}

// ─── Screen ──────────────────────────────────────────────────────────────

export default function ReportsScreen() {
  const { session, selectedLocation, userRole } = useAuth()
  const router = useRouter()
  const email = session?.user?.email ?? ''
  const isOwner = userRole === 'admin' || isOwnerEmail(email, userRole)

  const [rangeKey, setRangeKey] = useState<RangeKey>('week')
  const [instrFilter, setInstrFilter] = useState<string | null>(null)
  const [rptSportFilter, setRptSportFilter] = useState<string>('all')
  const [sortCol, setSortCol] = useState<string>('revenue')
  const [sortAsc, setSortAsc] = useState(false)

  const toggleSort = (col: string) => {
    if (sortCol === col) setSortAsc(!sortAsc)
    else { setSortCol(col); setSortAsc(false) }
  }

  const range = getRange(rangeKey)
  const prevRange = getPrevRange(rangeKey)

  // Current period data
  const { data: bookings, isLoading } = useQuery({
    queryKey: ['reports', range.from, range.to, selectedLocation, range.season],
    queryFn: () => fetchBookings(range.from, range.to, selectedLocation, range.season !== 'current' ? range.season : undefined),
    staleTime: 30000,
  })

  // Instructor rates — both individual and group
  const { data: instrRates } = useQuery({
    queryKey: ['instr-rates', selectedLocation],
    queryFn: async () => {
      const { data } = await supabase.from('instructors').select('first_name, last_name, hourly_rate')
      const map: Record<string, number> = {}
      for (const i of data ?? []) {
        map[`${i.first_name} ${i.last_name}`.trim()] = Number(i.hourly_rate) || 0
      }
      return map
    },
  })

  // Previous period data (for comparison)
  const { data: prevBookings } = useQuery({
    queryKey: ['reports-prev', prevRange.from, prevRange.to, selectedLocation, prevRange.season],
    queryFn: () => fetchBookings(prevRange.from, prevRange.to, selectedLocation, prevRange.season !== 'current' ? prevRange.season : undefined),
    staleTime: 30000,
  })

  // ── Compute metrics ──
  const metrics = useMemo(() => {
    if (!bookings) return null

    // Separate bosman (school operations) from teaching
    let filtered = bookings
    if (rptSportFilter !== 'all') {
      filtered = bookings.filter(b => b.service_name_snap.toLowerCase().includes(rptSportFilter.toLowerCase()))
    }
    const teachingBookings = filtered.filter(b => !isBosman(b.service_name_snap))
    const bosmanBookings = bookings.filter(b => isBosman(b.service_name_snap))
    const bosmanHours = bosmanBookings.reduce((s, b) => s + getDurationH(b), 0)

    const paid = teachingBookings.filter(b => b.payment_status === 'paid')
    const paidWithPrice = paid.filter(b => toPLN(b.total_price, b.currency) > 0)
    const revenuePLN = paid.reduce((s, b) => s + toPLN(b.total_price, b.currency), 0)
    const revenueAllPLN = teachingBookings.reduce((s, b) => s + toPLN(b.total_price, b.currency), 0)
    const unpaidRevenuePLN = revenueAllPLN - revenuePLN
    const totalHours = teachingBookings.reduce((s, b) => s + getDurationH(b), 0)
    const totalPersons = teachingBookings.reduce((s, b) => s + (b.persons || 1), 0)
    const avgPerPerson = totalPersons > 0 ? Math.round(revenuePLN / totalPersons) : 0
    const avgPerBooking = paidWithPrice.length > 0 ? Math.round(revenuePLN / paidWithPrice.length) : 0

    // Revenue by day
    const byDay: Record<string, number> = {}
    const countByDay: Record<string, number> = {}
    for (const b of bookings) {
      byDay[b.start_date] = (byDay[b.start_date] || 0) + (b.payment_status === 'paid' ? toPLN(b.total_price, b.currency) : 0)
      countByDay[b.start_date] = (countByDay[b.start_date] || 0) + 1
    }

    // Fill in timeline — weekly aggregation for long ranges, daily for short
    const days = differenceInDays(parseISO(range.to), parseISO(range.from)) + 1
    const revenueTimeline: LineDatum[] = []
    const bookingsTimeline: BarDatum[] = []

    if (days > 60) {
      // Weekly aggregation for seasons/long ranges
      const weeks = Math.ceil(days / 7)
      for (let w = 0; w < weeks; w++) {
        const weekStart = addDays(parseISO(range.from), w * 7)
        let weekRev = 0
        let weekCount = 0
        for (let d = 0; d < 7; d++) {
          const dateStr = format(addDays(weekStart, d), 'yyyy-MM-dd')
          weekRev += byDay[dateStr] || 0
          weekCount += countByDay[dateStr] || 0
        }
        const label = format(weekStart, 'd MMM')
        revenueTimeline.push({ label, value: Math.round(weekRev) })
        bookingsTimeline.push({ label, value: weekCount })
      }
    } else {
      // Daily for short ranges
      for (let i = 0; i < days; i++) {
        const d = format(addDays(parseISO(range.from), i), 'yyyy-MM-dd')
        const label = format(parseISO(d), 'd MMM')
        revenueTimeline.push({ label, value: Math.round(byDay[d] || 0) })
        bookingsTimeline.push({ label, value: countByDay[d] || 0 })
      }
    }

    // Sport breakdown — PLN per hour per sport (excluding bosman)
    const sportMap: Record<string, { revenue: number; revenueAll: number; hours: number; count: number; custHours: number }> = {}
    for (const b of teachingBookings) {
      const sport = extractSport(b.service_name_snap)
      if (!sportMap[sport]) sportMap[sport] = { revenue: 0, revenueAll: 0, hours: 0, count: 0, custHours: 0 }
      sportMap[sport].count++
      const h = getDurationH(b)
      sportMap[sport].hours += h
      sportMap[sport].custHours += h * b.persons
      const price = toPLN(b.total_price, b.currency)
      sportMap[sport].revenueAll += price
      if (b.payment_status === 'paid') sportMap[sport].revenue += price
    }
    const sports = Object.entries(sportMap)
      .map(([sport, d]) => ({ sport, ...d, perHour: d.hours > 0 ? Math.round(d.revenue / d.hours) : 0, perHourAll: d.hours > 0 ? Math.round(d.revenueAll / d.hours) : 0 }))
      .filter(s => s.count > 0 && s.sport !== 'Inne')
      .sort((a, b) => b.revenue - a.revenue)

    // Instructor breakdown with profitability
    const instrMap: Record<string, { revenue: number; revenueAll: number; hours: number; count: number; custHours: number }> = {}
    for (const b of teachingBookings) {
      const name = b.instructor_snap || 'Brak'
      if (!instrMap[name]) instrMap[name] = { revenue: 0, revenueAll: 0, hours: 0, count: 0, custHours: 0 }
      instrMap[name].count++
      const h = getDurationH(b)
      instrMap[name].hours += h
      instrMap[name].custHours += h * b.persons
      const price = toPLN(b.total_price, b.currency)
      instrMap[name].revenueAll += price
      if (b.payment_status === 'paid') instrMap[name].revenue += price
    }
    // Compute cost per booking based on category (excluding bosman from instructor profitability)
    const rates = instrRates ?? {}
    const instrCostMap: Record<string, number> = {}
    for (const b of teachingBookings) {
      const name = b.instructor_snap || 'Brak'
      const baseRate = rates[name] ?? 0
      if (!baseRate) continue
      const h = getDurationH(b)
      const svcLower = b.service_name_snap.toLowerCase()
      // Grupowa/podwójna = +10-15 PLN/h vs indywidualna
      const isGroup = svcLower.includes('grupow') || svcLower.includes('podwójn') || svcLower.includes('podwojn')
      const effectiveRate = isGroup ? Math.round(baseRate * 1.15) : baseRate
      instrCostMap[name] = (instrCostMap[name] ?? 0) + h * effectiveRate
    }

    const instructors = Object.entries(instrMap)
      .map(([name, d]) => {
        const rate = rates[name] ?? 0
        const cost = instrCostMap[name] ?? 0
        const profit = d.revenue - cost
        const margin = d.revenue > 0 ? Math.round((profit / d.revenue) * 100) : 0
        return { name, ...d, rate, cost, profit, margin, perHour: d.hours > 0 ? Math.round(d.revenue / d.hours) : 0 }
      })
      .filter(i => i.name !== 'Brak' && i.hours > 0)
      .sort((a, b) => b.revenue - a.revenue)

    // Averages
    const avgRevenuePerHour = totalHours > 0 ? Math.round(revenuePLN / totalHours) : 0
    const totalInstrCost = instructors.reduce((s, i) => s + i.cost, 0)
    const totalProfit = revenuePLN - totalInstrCost

    // Bosman cost (school operations — separate from teaching)
    let bosmanCost = 0
    for (const b of bosmanBookings) {
      const name = b.instructor_snap || ''
      const rate = rates[name] ?? 0
      bosmanCost += getDurationH(b) * rate
    }

    // Fixed costs per SEASON (Apr-Oct = 1 season)
    // Bosman is also a fixed seasonal cost (brutto per season, not hourly)
    const SEASON_FIXED_COSTS = {
      baza: 350000,       // rent/lease per season
      bosman: 60000,      // bosman brutto per season
      paliwo: 15000,      // fuel for boat per season
      konserwacja: 10000, // maintenance per season
      ubezpieczenie: 8000,// insurance per season
      inne: 5000,         // other per season
    }
    const totalFixedCosts = Object.values(SEASON_FIXED_COSTS).reduce((a, b) => a + b, 0)

    // Fixed costs = full season (not proportional)
    // Net profit = revenue - instructor cost - full season fixed costs
    const netProfit = revenuePLN - totalInstrCost - totalFixedCosts

    // No-show
    const noShowCount = teachingBookings.filter(b => b.booking_status === 'no_show').length
    const completedCount = teachingBookings.filter(b => ['completed', 'no_show'].includes(b.booking_status)).length
    const noShowRate = completedCount > 0 ? Math.round((noShowCount / completedCount) * 100) : 0

    // Cost per hour — ONLY fixed costs (baza+bosman+paliwo+...) / sport hours
    // Instructors are separate — they have margin, user adds them himself
    const fixedCostPerHour = totalHours > 0 ? Math.round(totalFixedCosts / totalHours) : 0
    const instrCostPerHour = totalHours > 0 ? Math.round(totalInstrCost / totalHours) : 0
    const costPerHourTotal = fixedCostPerHour // only fixed, no instructors
    const profitPerHour = avgRevenuePerHour - fixedCostPerHour - instrCostPerHour

    // Sport profitability — per sport: revenue/h - fixed/h = margin before instructor
    const sportProfit = sports.map(sp => ({
      ...sp,
      fixedCostH: fixedCostPerHour,
      marginH: sp.perHour - fixedCostPerHour,
    }))

    return { revenuePLN, revenueAllPLN, unpaidRevenuePLN, totalBookings: teachingBookings.length, totalPersons, avgPerPerson, avgPerBooking, paidCount: paidWithPrice.length, totalHours, bosmanHours, bosmanCost, revenueTimeline, bookingsTimeline, instructors, sports, sportProfit, noShowCount, noShowRate, avgRevenuePerHour, totalInstrCost, totalProfit, netProfit, costPerHourTotal, fixedCostPerHour, instrCostPerHour, profitPerHour, totalFixedCosts }
  }, [bookings, range, instrRates, rptSportFilter])

  // Previous period metrics for comparison
  const prevMetrics = useMemo(() => {
    if (!prevBookings) return null
    const paid = prevBookings.filter(b => b.payment_status === 'paid')
    const revenuePLN = paid.reduce((s, b) => s + toPLN(b.total_price, b.currency), 0)
    const totalHours = prevBookings.reduce((s, b) => s + getDurationH(b), 0)
    const noShowCount = prevBookings.filter(b => b.booking_status === 'no_show').length
    return { revenuePLN, totalBookings: prevBookings.length, totalHours, noShowCount }
  }, [prevBookings])

  // Deltas
  const revDelta = metrics && prevMetrics ? delta(metrics.revenuePLN, prevMetrics.revenuePLN) : null
  const bookDelta = metrics && prevMetrics ? delta(metrics.totalBookings, prevMetrics.totalBookings) : null
  const hoursDelta = metrics && prevMetrics ? delta(metrics.totalHours, prevMetrics.totalHours) : null
  const noShowDelta = metrics && prevMetrics ? delta(metrics.noShowCount, prevMetrics.noShowCount) : null

  if (!isOwner) {
    return (
      <View style={s.center}>
        <Ionicons name="lock-closed-outline" size={40} color={C.textMuted} />
        <Text style={s.lockText}>Raporty dostępne tylko dla właścicieli</Text>
        <TouchableOpacity onPress={() => router.back()} style={s.backLink}><Text style={s.backLinkText}>Wróć</Text></TouchableOpacity>
      </View>
    )
  }

  const maxInstrRev = metrics ? Math.max(...metrics.instructors.map(i => i.revenue), 1) : 1
  const prevLabel = rangeKey === 'today' ? 'wczoraj' : rangeKey === 'week' ? 'ost. tydz.' : rangeKey === 'month' ? 'ost. mies.' : 'sezon 2025'

  return (
    <View style={s.root}>
      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.headerBack}>
          <Ionicons name="chevron-back" size={20} color={C.textSec} />
        </TouchableOpacity>
        <Text style={s.headerTitle}>Raporty</Text>
        {Platform.OS === 'web' && (
          <TouchableOpacity onPress={() => {
            if (!metrics) return
            const locLabel = selectedLocation === 'hel' ? 'Hel' : selectedLocation === 'hurghada' ? 'Hurghada' : 'Wszystkie'
            generateReport({
              rangeLabel: RANGE_LABELS[rangeKey] + ' (' + range.from + ' - ' + range.to + ')',
              location: locLabel,
              generatedAt: format(new Date(), 'dd.MM.yyyy HH:mm'),
              revenuePLN: metrics.revenuePLN,
              totalBookings: metrics.totalBookings,
              totalHours: metrics.totalHours,
              noShowCount: metrics.noShowCount,
              noShowRate: metrics.noShowRate,
              avgRevenuePerHour: metrics.avgRevenuePerHour,
              totalInstrCost: metrics.totalInstrCost,
              bosmanCost: metrics.bosmanCost,
              bosmanHours: metrics.bosmanHours,
              fixedCostForPeriod: metrics.totalFixedCosts,
              netProfit: metrics.netProfit,
              revDelta: revDelta ?? null,
              bookDelta: bookDelta ?? null,
              hoursDelta: hoursDelta ?? null,
              noShowDelta: noShowDelta ?? null,
              instructors: metrics.instructors,
              sports: metrics.sports,
            })
          }} style={s.printBtn} activeOpacity={0.7}>
            <Ionicons name="print-outline" size={16} color={C.primary} />
            <Text style={s.printText}>Drukuj raport</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Range chips */}
      <View style={s.chipRow}>
        {(Object.keys(RANGE_LABELS) as RangeKey[]).map(k => (
          <TouchableOpacity
            key={k}
            style={[s.chip, rangeKey === k && s.chipActive]}
            onPress={() => setRangeKey(k)}
            activeOpacity={0.7}
          >
            <Text style={[s.chipText, rangeKey === k && s.chipTextActive]}>{RANGE_LABELS[k]}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Sport filter */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ maxHeight: 36, backgroundColor: C.surface }} contentContainerStyle={{ gap: 5, paddingHorizontal: 20, alignItems: 'center', paddingVertical: 4 }}>
        {[
          { key: 'all', label: 'Wsz. sporty', icon: '🏫' },
          { key: 'kite', label: 'Kite', icon: '🪁' },
          { key: 'wind', label: 'Wind', icon: '🏄' },
          { key: 'wing', label: 'Wing', icon: '🦅' },
          { key: 'desko', label: 'Carver', icon: '🛹' },
          { key: 'sup', label: 'SUP', icon: '🚣' },
        ].map(f => (
          <TouchableOpacity
            key={f.key}
            onPress={() => setRptSportFilter(f.key === 'all' ? 'all' : f.key)}
            style={[s.chip, rptSportFilter === f.key && s.chipActive]}
            activeOpacity={0.7}
          >
            <Text style={[s.chipText, rptSportFilter === f.key && s.chipTextActive]}>{f.icon} {f.label}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {isLoading ? (
        <View style={s.center}><ActivityIndicator size="large" color={C.primary} /></View>
      ) : !metrics ? (
        <View style={s.center}><Text style={{ color: C.textMuted }}>Brak danych</Text></View>
      ) : (
        <ScrollView style={s.scroll} contentContainerStyle={{ paddingBottom: 40 }} showsVerticalScrollIndicator={true}>

          {/* ── Comparison cards ── */}
          <View style={s.compRow}>
            <CompCard label="Przychód (opłacone)" value={fmtMoney(metrics.revenuePLN)} delta={revDelta} prevLabel={prevLabel} icon="cash-outline" color={C.success}
              breakdown={[
                `${metrics.paidCount} rez. ze statusem "opłacone"`,
                `${fmtMoney(metrics.revenuePLN)} ÷ ${metrics.totalPersons} os. = ${metrics.avgPerPerson} PLN/os.`,
                `${fmtMoney(metrics.revenuePLN)} ÷ ${Math.round(metrics.totalHours)}h = ${metrics.avgRevenuePerHour} ${getCurrencySymbol()}/h`,
              ]}
            />
            <CompCard label="Przychód (wszystkie)" value={fmtMoney(metrics.revenueAllPLN)} delta={null} prevLabel="" icon="wallet-outline" color={'#0284c7'}
              breakdown={[
                `Wartość WSZYSTKICH lekcji`,
                metrics.unpaidRevenuePLN > 0 ? `Do ściągnięcia: ${fmtMoney(metrics.unpaidRevenuePLN)}` : `Wszystko opłacone`,
              ]}
            />
          </View>
          <View style={s.compRow}>
            <CompCard label="Rezerwacje" value={String(metrics.totalBookings)} delta={bookDelta} prevLabel={prevLabel} icon="calendar-outline" color={C.primary}
              breakdown={[
                `Lekcje sportowe (bez bosmana)`,
                `Śr. ${metrics.totalHours > 0 ? (metrics.totalBookings / Math.max(1, Math.round(metrics.totalHours / 8))).toFixed(1) : 0} rez./dzień pracy`,
              ]}
            />
          </View>
          <View style={s.compRow}>
            <CompCard label="Godziny" value={`${Math.round(metrics.totalHours)}h`} delta={hoursDelta} prevLabel={prevLabel} icon="time-outline" color={C.purple}
              breakdown={[
                `Godziny lekcji (sporty)`,
                `+ ${Math.round(metrics.bosmanHours)}h bosman (osobno)`,
                `Śr. ${metrics.avgRevenuePerHour} ${getCurrencySymbol()} przychodu/h`,
              ]}
            />
            <CompCard label="No-show" value={`${metrics.noShowCount} (${metrics.noShowRate}%)`} delta={noShowDelta ? { ...noShowDelta, positive: !noShowDelta.positive } : null} prevLabel={prevLabel} icon="person-remove-outline" color={C.error}
              breakdown={[
                `Nieobecności / zakończone lekcje`,
                `${metrics.noShowCount} z ${metrics.totalBookings} rezerwacji`,
              ]}
            />
          </View>
          <View style={s.compRow}>
            <CompCard label="Koszt stały / godzinę" value={`${metrics.costPerHourTotal} ${getCurrencySymbol()}`} delta={null} prevLabel="" icon="calculator-outline" color={C.warning}
              breakdown={[
                `Baza: 350k + Bosman: 60k`,
                `Paliwo+kons.+ubezp.: 38k`,
                `────────────────`,
                `${fmtMoney(metrics.totalFixedCosts)} ÷ ${Math.round(metrics.totalHours)}h`,
                `Bez wypłat instruktorów`,
              ]}
            />
            <CompCard label="Zysk / godzinę" value={`${metrics.profitPerHour} ${getCurrencySymbol()}`} delta={null} prevLabel="" icon="trending-up-outline" color={metrics.profitPerHour > 0 ? C.success : C.error}
              breakdown={[
                `Przychód: ${metrics.avgRevenuePerHour} ${getCurrencySymbol()}/h`,
                `- Koszty stałe: ${metrics.fixedCostPerHour} ${getCurrencySymbol()}/h`,
                `- Instruktor: ${metrics.instrCostPerHour} ${getCurrencySymbol()}/h`,
                `────────────────`,
                `= ${metrics.profitPerHour} ${getCurrencySymbol()} netto/h`,
              ]}
            />
          </View>

          {/* ── Margin per sport (revenue - fixed costs only) ── */}
          {metrics.sportProfit.length > 0 && (
            <View style={s.card}>
              <Text style={s.sectionTitle}>Marża sportu / godzinę</Text>
              <Text style={s.sectionSub}>Przychód/h − koszty stałe ({metrics.fixedCostPerHour} ${getCurrencySymbol()}/h) = marża na instruktora</Text>
              <View style={s.tblHeader}>
                <Text style={[s.tblH, { flex: 2 }]}>Sport</Text>
                <Text style={[s.tblH, { width: 70 }]}>Przych/h</Text>
                <Text style={[s.tblH, { width: 70 }]}>Koszt stały/h</Text>
                <Text style={[s.tblH, { width: 70 }]}>Marża/h</Text>
                <Text style={[s.tblH, { width: 50 }]}>Godz.</Text>
              </View>
              {metrics.sportProfit.map((sp, idx) => (
                <View key={sp.sport} style={[s.tblRow, idx % 2 === 1 && { backgroundColor: C.surfaceAlt }]}>
                  <Text style={[s.tblCell, { flex: 2, fontWeight: '700' }]}>{sp.sport}</Text>
                  <Text style={[s.tblCell, { width: 70, color: C.success }]}>{sp.perHour} {getCurrencySymbol()}</Text>
                  <Text style={[s.tblCell, { width: 70, color: C.error }]}>-{sp.fixedCostH} {getCurrencySymbol()}</Text>
                  <Text style={[s.tblCell, { width: 70, fontWeight: '800', color: sp.marginH >= 0 ? C.success : C.error }]}>{sp.marginH} {getCurrencySymbol()}</Text>
                  <Text style={[s.tblCell, { width: 50 }]}>{Math.round(sp.hours)}h</Text>
                </View>
              ))}
            </View>
          )}

          {/* ── Revenue line chart ── */}
          <View style={s.card}>
            <Text style={s.sectionTitle}>Przychód w czasie {metrics.revenueTimeline.length > 31 ? '(tygodniowo)' : ''}</Text>
            <Text style={s.sectionSub}>{RANGE_LABELS[rangeKey]} · opłacone · PLN</Text>
            {metrics.revenueTimeline.length >= 2 ? (
              <LineChart data={metrics.revenueTimeline} lineColor={C.success} height={200} />
            ) : (
              <Text style={s.noData}>Za mało danych do wykresu</Text>
            )}
          </View>

          {/* ── Bookings bar chart ── */}
          <View style={s.card}>
            <Text style={s.sectionTitle}>Rezerwacje {metrics.bookingsTimeline.length > 31 ? '(tygodniowo)' : 'dziennie'}</Text>
            <Text style={s.sectionSub}>{RANGE_LABELS[rangeKey]} · wszystkie statusy</Text>
            {metrics.bookingsTimeline.length > 0 ? (
              <BarChart data={metrics.bookingsTimeline} barColor={C.primary} height={180} />
            ) : (
              <Text style={s.noData}>Brak rezerwacji w tym okresie</Text>
            )}
          </View>

          {/* ── Instructor revenue ── */}
          <View style={s.card}>
            <Text style={s.sectionTitle}>Przychód wg instruktora</Text>
            <Text style={s.sectionSub}>{RANGE_LABELS[rangeKey]} · oplacone vs wszystkie</Text>
            <View style={s.tblHeader}>
              <Text style={[s.tblH, { flex: 2 }]}>Instruktor</Text>
              <Text style={[s.tblH, { width: 45 }]}>Godz.</Text>
              <Text style={[s.tblH, { width: 40 }]}>Rez.</Text>
              <Text style={[s.tblH, { width: 70 }]}>Oplacone</Text>
              <Text style={[s.tblH, { width: 60 }]}>PLN/h</Text>
              <Text style={[s.tblH, { width: 70 }]}>Wszystkie</Text>
              <Text style={[s.tblH, { width: 60 }]}>PLN/h</Text>
            </View>
            {metrics.instructors.map((instr, idx) => (
              <TouchableOpacity key={instr.name} style={[s.tblRow, idx % 2 === 1 && { backgroundColor: C.surfaceAlt }, instrFilter === instr.name && { backgroundColor: C.primarySoft, borderLeftWidth: 3, borderLeftColor: C.primary }]} onPress={() => setInstrFilter(instrFilter === instr.name ? null : instr.name)} activeOpacity={0.7}>
                <Text style={[s.tblCell, { flex: 2, fontWeight: '700' }]} numberOfLines={1}>{instr.name}</Text>
                <Text style={[s.tblCell, { width: 45 }]}>{Math.round(instr.hours)}</Text>
                <Text style={[s.tblCell, { width: 40 }]}>{instr.count}</Text>
                <Text style={[s.tblCell, { width: 70, color: '#059669' }]}>{fmtMoney(instr.revenue)}</Text>
                <Text style={[s.tblCell, { width: 60, color: '#059669', fontWeight: '700' }]}>{instr.perHour}</Text>
                <Text style={[s.tblCell, { width: 70, color: '#0284c7' }]}>{fmtMoney(instr.revenueAll)}</Text>
                <Text style={[s.tblCell, { width: 60, color: '#0284c7', fontWeight: '700' }]}>{instr.hours > 0 ? Math.round(instr.revenueAll / instr.hours) : 0}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* ── Top instruktorzy wg godzin ── */}
          <View style={s.card}>
            <Text style={s.sectionTitle}>🏅 Ranking instruktorów (godziny)</Text>
            <Text style={s.sectionSub}>Kto przepracowal najwiecej godzin w tym okresie</Text>
            {(() => {
              const sorted = [...metrics.instructors].filter(i => i.name !== 'Brak' && i.hours > 0).sort((a, b) => b.hours - a.hours).slice(0, 15)
              const maxH = sorted.length > 0 ? sorted[0].hours : 1
              return sorted.map((instr, idx) => (
                <View key={instr.name} style={s.occRow}>
                  <Text style={[s.occRank, { color: idx < 3 ? '#f59e0b' : '#94a3b8' }]}>{idx < 3 ? ['🥇','🥈','🥉'][idx] : `${idx + 1}.`}</Text>
                  <Text style={s.occName} numberOfLines={1}>{instr.name}</Text>
                  <View style={s.occBarWrap}>
                    <View style={s.occBarBg} />
                    <View style={[s.occBarFill, { width: `${(instr.hours / maxH) * 100}%` as any, backgroundColor: C.primary }]} />
                  </View>
                  <Text style={s.occDetail}>{Math.round(instr.hours)}h</Text>
                  <Text style={[s.occPct, { color: '#059669' }]}>{instr.count} rez.</Text>
                </View>
              ))
            })()}
          </View>

          {/* ── Sport profitability — per hour per sport ── */}
          <View style={s.card}>
            <Text style={s.sectionTitle}>💰 Przychód za 1h sportu</Text>
            <Text style={s.sectionSub}>Oplacone = faktyczny przychod · Wszystkie = z nieoplaconymi</Text>
            <View style={s.tblHeader}>
              <Text style={[s.tblH, { flex: 2 }]}>Sport</Text>
              <Text style={[s.tblH, { width: 55 }]}>Godz.</Text>
              <Text style={[s.tblH, { width: 45 }]}>Rez.</Text>
              <Text style={[s.tblH, { width: 75 }]}>Oplacone</Text>
              <Text style={[s.tblH, { width: 75 }]}>PLN/h opl.</Text>
              <Text style={[s.tblH, { width: 75 }]}>Wszystkie</Text>
              <Text style={[s.tblH, { width: 75 }]}>PLN/h wsz.</Text>
            </View>
            {metrics.sports.map((sp, idx) => (
              <View key={sp.sport} style={[s.tblRow, idx % 2 === 1 && { backgroundColor: C.surfaceAlt }]}>
                <Text style={[s.tblCell, { flex: 2, fontWeight: '700' }]}>{sp.sport}</Text>
                <Text style={[s.tblCell, { width: 55 }]}>{Math.round(sp.hours)}h</Text>
                <Text style={[s.tblCell, { width: 45 }]}>{sp.count}</Text>
                <Text style={[s.tblCell, { width: 75, color: '#059669' }]}>{fmtMoney(sp.revenue)}</Text>
                <Text style={[s.tblCell, { width: 75, color: '#059669', fontWeight: '800' }]}>{sp.perHour} {getCurrencySymbol()}</Text>
                <Text style={[s.tblCell, { width: 75, color: '#0284c7' }]}>{fmtMoney(sp.revenueAll)}</Text>
                <Text style={[s.tblCell, { width: 75, color: '#0284c7', fontWeight: '800' }]}>{sp.perHourAll} {getCurrencySymbol()}</Text>
              </View>
            ))}
          </View>

          {/* ── Instructor profitability table ── */}
          <View style={s.card}>
            <Text style={s.sectionTitle}>👨‍🏫 Rentownosc instruktorow</Text>
            <Text style={s.sectionSub}>Przychod od kursantow − koszt instruktora = zysk</Text>
            <Text style={s.legend}>Stawka = hourly_rate z profilu · Margin = (przychod − koszt) / przychod</Text>

            {/* Full P&L summary */}
            <View style={s.profitSummary}>
              <View style={s.profitSumItem}>
                <Text style={s.profitSumLabel}>Przychod (oplacone)</Text>
                <Text style={[s.profitSumValue, { color: C.success }]}>{fmtMoney(metrics.revenuePLN)}</Text>
                {metrics.unpaidRevenuePLN > 0 && <Text style={{ color: '#0284c7', fontSize: 10, marginTop: 2 }}>+ {fmtMoney(metrics.unpaidRevenuePLN)} do sciagniecia</Text>}
              </View>
              <Text style={s.profitSumMinus}>−</Text>
              <View style={s.profitSumItem}>
                <Text style={s.profitSumLabel}>Instruktorzy</Text>
                <Text style={[s.profitSumValue, { color: C.error }]}>{fmtMoney(metrics.totalInstrCost)}</Text>
              </View>
              <Text style={s.profitSumMinus}>−</Text>
              <View style={s.profitSumItem}>
                <Text style={s.profitSumLabel}>Koszty stale (sezon)</Text>
                <Text style={[s.profitSumValue, { color: C.error }]}>{fmtMoney(metrics.totalFixedCosts)}</Text>
              </View>
              <Text style={s.profitSumMinus}>=</Text>
              <View style={s.profitSumItem}>
                <Text style={s.profitSumLabel}>Wynik netto</Text>
                <Text style={[s.profitSumValue, { color: metrics.netProfit >= 0 ? C.success : C.error, fontSize: 22 }]}>{fmtMoney(metrics.netProfit)}</Text>
              </View>
            </View>

            {/* Fixed costs breakdown */}
            <View style={{ flexDirection: 'row', gap: 8, marginBottom: 14 }}>
              <View style={[s.profitDetailCard, { flex: 1 }]}>
                <Text style={{ fontSize: 18 }}>🏠</Text>
                <Text style={s.profitDetailLabel}>Baza</Text>
                <Text style={s.profitDetailValue}>350k PLN</Text>
                <Text style={[s.profitDetailCost, { color: C.error }]}>brutto / sezon</Text>
              </View>
              <View style={[s.profitDetailCard, { flex: 1 }]}>
                <Text style={{ fontSize: 18 }}>⛵</Text>
                <Text style={s.profitDetailLabel}>Bosman</Text>
                <Text style={s.profitDetailValue}>60k PLN</Text>
                <Text style={[s.profitDetailCost, { color: C.warning }]}>brutto / sezon</Text>
              </View>
              <View style={[s.profitDetailCard, { flex: 1 }]}>
                <Text style={{ fontSize: 18 }}>⚙️</Text>
                <Text style={s.profitDetailLabel}>Pozostałe</Text>
                <Text style={s.profitDetailValue}>38k PLN</Text>
                <Text style={[s.profitDetailCost, { color: C.textMuted }]}>paliwo+kons.+ubezp.</Text>
              </View>
              <View style={[s.profitDetailCard, { flex: 1 }]}>
                <Text style={{ fontSize: 18 }}>🏄</Text>
                <Text style={s.profitDetailLabel}>Sporty</Text>
                <Text style={s.profitDetailValue}>{Math.round(metrics.totalHours)}h</Text>
                <Text style={[s.profitDetailCost, { color: C.success }]}>{metrics.costPerHourTotal} ${getCurrencySymbol()}/h koszt</Text>
              </View>
            </View>

            {/* Table header — clickable to sort */}
            <View style={s.tblHeader}>
              {[
                { key: 'name', label: 'Instruktor', flex: 2 },
                { key: 'hours', label: 'Godz.', w: 45 },
                { key: 'rate', label: 'Stawka', w: 50 },
                { key: 'cost', label: 'Koszt', w: 65 },
                { key: 'revenue', label: 'Oplacone', w: 70 },
                { key: 'revenueAll', label: 'Wszystkie', w: 70 },
                { key: 'profit', label: 'Zysk', w: 65 },
                { key: 'perHour', label: getCurrencySymbol() + '/h', w: 50 },
                { key: 'margin', label: 'Marza', w: 45 },
              ].map(col => (
                <TouchableOpacity
                  key={col.key}
                  style={[col.flex ? { flex: col.flex } : { width: col.w }]}
                  onPress={() => toggleSort(col.key)}
                  activeOpacity={0.6}
                >
                  <Text style={[s.tblH, sortCol === col.key && { color: '#0284c7' }]}>
                    {col.label} {sortCol === col.key ? (sortAsc ? '↑' : '↓') : ''}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Table rows — sorted */}
            {[...metrics.instructors].sort((a: any, b: any) => {
              const va = a[sortCol] ?? 0, vb = b[sortCol] ?? 0
              if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va)
              return sortAsc ? va - vb : vb - va
            }).map((instr, idx) => (
              <TouchableOpacity key={instr.name} style={[s.tblRow, idx % 2 === 1 && { backgroundColor: C.surfaceAlt }, instrFilter === instr.name && { backgroundColor: C.primarySoft, borderLeftWidth: 3, borderLeftColor: C.primary }]} onPress={() => setInstrFilter(instrFilter === instr.name ? null : instr.name)} activeOpacity={0.7}>
                <Text style={[s.tblCell, { flex: 2, fontWeight: '700', color: instrFilter === instr.name ? C.primary : C.text }]} numberOfLines={1}>{instr.name}</Text>
                <Text style={[s.tblCell, { width: 45 }]}>{Math.round(instr.hours)}</Text>
                <Text style={[s.tblCell, { width: 50 }]}>{instr.rate > 0 ? `${instr.rate}` : '—'}</Text>
                <Text style={[s.tblCell, { width: 65, color: '#dc2626' }]}>{instr.cost > 0 ? fmtMoney(instr.cost) : '—'}</Text>
                <Text style={[s.tblCell, { width: 70, color: '#059669', fontWeight: '700' }]}>{fmtMoney(instr.revenue)}</Text>
                <Text style={[s.tblCell, { width: 70, color: '#0284c7' }]}>{fmtMoney(instr.revenueAll)}</Text>
                <Text style={[s.tblCell, { width: 65, color: instr.profit >= 0 ? '#059669' : '#dc2626', fontWeight: '800' }]}>
                  {instr.rate > 0 ? fmtMoney(instr.profit) : '—'}
                </Text>
                <Text style={[s.tblCell, { width: 50, fontWeight: '700' }]}>{instr.perHour}</Text>
                <View style={{ width: 45, alignItems: 'center' }}>
                  {instr.rate > 0 ? (
                    <View style={[s.marginBadge, { backgroundColor: instr.margin >= 50 ? '#dcfce7' : instr.margin >= 30 ? '#fef3c7' : '#fee2e2' }]}>
                      <Text style={[s.marginText, { color: instr.margin >= 50 ? '#16a34a' : instr.margin >= 30 ? '#d97706' : '#dc2626' }]}>{instr.margin}%</Text>
                    </View>
                  ) : <Text style={s.tblCell}>—</Text>}
                </View>
              </TouchableOpacity>
            ))}
          </View>

          {/* ── Selected instructor detail card ── */}
          {instrFilter && (() => {
            const instr = metrics.instructors.find(i => i.name === instrFilter)
            if (!instr) return null
            const instrBookings = bookings?.filter(b => b.instructor_snap === instrFilter) ?? []
            const instrSports: Record<string, { count: number; hours: number; revenue: number; revenueAll: number }> = {}
            let totalRevenueAll = 0
            for (const b of instrBookings) {
              const sp = extractSport(b.service_name_snap)
              if (!instrSports[sp]) instrSports[sp] = { count: 0, hours: 0, revenue: 0, revenueAll: 0 }
              instrSports[sp].count++
              instrSports[sp].hours += getDurationH(b)
              const price = toPLN(b.total_price, b.currency)
              instrSports[sp].revenueAll += price
              totalRevenueAll += price
              if (b.payment_status === 'paid') instrSports[sp].revenue += price
            }
            const paidCount = instrBookings.filter(b => b.payment_status === 'paid').length
            const unpaidCount = instrBookings.filter(b => b.payment_status === 'unpaid').length
            const unpaidRevenue = totalRevenueAll - instr.revenue
            return (
              <View style={[s.card, Platform.OS === 'web' && { background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)' } as any]}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <Text style={[s.sectionTitle, { marginBottom: 0 }]}>👨‍🏫 {instrFilter}</Text>
                  <TouchableOpacity onPress={() => setInstrFilter(null)} style={{ padding: 4 }}>
                    <Ionicons name="close-circle" size={22} color="#94a3b8" />
                  </TouchableOpacity>
                </View>

                <View style={{ flexDirection: 'row', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
                  <View style={s.instrDetailStat}>
                    <Text style={s.instrDetailLabel}>Godziny</Text>
                    <Text style={s.instrDetailValue}>{Math.round(instr.hours)}h</Text>
                  </View>
                  <View style={s.instrDetailStat}>
                    <Text style={s.instrDetailLabel}>Rezerwacje</Text>
                    <Text style={s.instrDetailValue}>{instr.count}</Text>
                  </View>
                  <View style={s.instrDetailStat}>
                    <Text style={s.instrDetailLabel}>Przychod (oplacone)</Text>
                    <Text style={[s.instrDetailValue, { color: '#059669' }]}>{fmtMoney(instr.revenue)}</Text>
                  </View>
                  <View style={s.instrDetailStat}>
                    <Text style={s.instrDetailLabel}>Przychod (wszystkie)</Text>
                    <Text style={[s.instrDetailValue, { color: '#0284c7' }]}>{fmtMoney(totalRevenueAll)}</Text>
                  </View>
                  {unpaidRevenue > 0 && <View style={s.instrDetailStat}>
                    <Text style={s.instrDetailLabel}>Do sciagniecia</Text>
                    <Text style={[s.instrDetailValue, { color: '#dc2626' }]}>{fmtMoney(unpaidRevenue)}</Text>
                  </View>}
                  <View style={s.instrDetailStat}>
                    <Text style={s.instrDetailLabel}>Stawka</Text>
                    <Text style={s.instrDetailValue}>{instr.rate} {getCurrencySymbol()}/h</Text>
                  </View>
                  <View style={s.instrDetailStat}>
                    <Text style={s.instrDetailLabel}>Koszt</Text>
                    <Text style={[s.instrDetailValue, { color: '#dc2626' }]}>{fmtMoney(instr.cost)}</Text>
                  </View>
                  <View style={s.instrDetailStat}>
                    <Text style={s.instrDetailLabel}>Zysk</Text>
                    <Text style={[s.instrDetailValue, { color: instr.profit >= 0 ? '#059669' : '#dc2626', fontWeight: '900' }]}>{fmtMoney(instr.profit)}</Text>
                  </View>
                  <View style={s.instrDetailStat}>
                    <Text style={s.instrDetailLabel}>getCurrencySymbol()/h (klient)</Text>
                    <Text style={[s.instrDetailValue, { fontWeight: '900' }]}>{instr.perHour}</Text>
                  </View>
                  <View style={s.instrDetailStat}>
                    <Text style={s.instrDetailLabel}>Marza</Text>
                    <Text style={[s.instrDetailValue, { color: instr.margin >= 50 ? '#059669' : instr.margin >= 30 ? '#d97706' : '#dc2626', fontWeight: '900' }]}>{instr.margin}%</Text>
                  </View>
                </View>

                <Text style={{ color: C.textSec, fontSize: 13, fontWeight: '800', marginBottom: 8 }}>Sporty</Text>
                {Object.entries(instrSports).map(([sport, d]) => (
                  <View key={sport} style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 4 }}>
                    <Text style={{ color: C.textSec, fontSize: 12, fontWeight: '600', width: 80 }}>{sport}</Text>
                    <Text style={{ color: C.textMuted, fontSize: 11 }}>
                      {d.count} rez. · {Math.round(d.hours)}h · {fmtMoney(d.revenue)}{d.revenueAll > d.revenue ? ` (${fmtMoney(d.revenueAll)} potenc.)` : ''}
                    </Text>
                  </View>
                ))}

                <Text style={{ color: C.textSec, fontSize: 13, fontWeight: '800', marginTop: 12, marginBottom: 6 }}>Platnosci</Text>
                <Text style={{ color: C.textMuted, fontSize: 12 }}>✅ Oplacone: {paidCount} · ❌ Nieoplacone: {unpaidCount}</Text>
              </View>
            )
          })()}

          {/* ── Avg revenue per hour KPI ── */}
          <View style={[s.card, Platform.OS === 'web' && { background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)' } as any]}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <Text style={{ fontSize: 36 }}>📈</Text>
              <View>
                <Text style={{ color: C.textMuted, fontSize: 12, fontWeight: '700', textTransform: 'uppercase' }}>Sredni przychod za 1h pracy</Text>
                <Text style={{ color: C.primary, fontSize: 32, fontWeight: '900', letterSpacing: -1 }}>{metrics.avgRevenuePerHour} ${getCurrencySymbol()}/h</Text>
              </View>
            </View>
          </View>

        </ScrollView>
      )}
    </View>
  )
}

// ─── Comparison Card ─────────────────────────────────────────────────────

function CompCard({
  label, value, delta: d, prevLabel, icon, color, breakdown,
}: {
  label: string; value: string; delta: ReturnType<typeof delta>; prevLabel: string
  icon: React.ComponentProps<typeof Ionicons>['name']; color: string
  breakdown?: string[]
}) {
  return (
    <View style={s.compCard}>
      <View style={s.compTopRow}>
        {/* Left: icon + label + value + delta */}
        <View style={s.compLeft}>
          <View style={[s.compIcon, { backgroundColor: color + '18' }]}>
            <Ionicons name={icon} size={18} color={color} />
          </View>
          <Text style={s.compLabel}>{label}</Text>
          <Text style={s.compValue}>{value}</Text>
          {d ? (
            <View style={[s.compDelta, { backgroundColor: d.positive ? C.successSoft : C.errorSoft }]}>
              <Ionicons name={d.positive ? 'trending-up' : 'trending-down'} size={12} color={d.positive ? C.success : C.error} />
              <Text style={[s.compDeltaText, { color: d.positive ? C.success : C.error }]}>{d.label}</Text>
            </View>
          ) : prevLabel ? (
            <Text style={s.compPrevLabel}>vs {prevLabel}</Text>
          ) : null}
        </View>
        {/* Right: breakdown legend */}
        {breakdown && breakdown.length > 0 && (
          <View style={s.compBreakdown}>
            {breakdown.map((line, i) => (
              <Text key={i} style={[s.compBreakdownText, line.startsWith('─') && s.compBreakdownDivider]}>{line}</Text>
            ))}
          </View>
        )}
      </View>
    </View>
  )
}

// ─── Styles ──────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  lockText: { color: C.textMuted, fontSize: 14, fontWeight: '600' },
  backLink: { paddingVertical: 8, paddingHorizontal: 20 },
  backLinkText: { color: C.primary, fontSize: 14, fontWeight: '700' },

  // Header
  header: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: C.surface, paddingTop: Platform.OS === 'web' ? 20 : 56,
    paddingBottom: 14, paddingHorizontal: 20,
    borderBottomWidth: 1, borderBottomColor: C.border,
  },
  headerBack: { width: 36, height: 36, borderRadius: 12, backgroundColor: C.surfaceHigh, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { flex: 1, color: C.text, fontSize: 20, fontWeight: '800' },
  printBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10,
    backgroundColor: C.primarySoft, borderWidth: 1, borderColor: C.primary + '30',
  },
  printText: { color: C.primary, fontSize: 13, fontWeight: '700' },

  // Chips
  chipRow: {
    flexDirection: 'row', gap: 6, paddingHorizontal: 20,
    paddingVertical: 12, backgroundColor: C.surface,
  },
  chip: {
    paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20,
    backgroundColor: C.surfaceHigh, borderWidth: 1, borderColor: C.border,
  },
  chipActive: { backgroundColor: C.primary + '18', borderColor: C.primary },
  chipText: { color: C.textMuted, fontSize: 12, fontWeight: '700' },
  chipTextActive: { color: C.primary },

  scroll: { flex: 1, paddingHorizontal: 20, paddingTop: 16 },

  // Comparison cards
  compRow: { flexDirection: 'row', gap: 10, marginBottom: 16 },
  compCard: {
    flex: 1, backgroundColor: C.surface, borderRadius: 16, padding: 14,
    borderWidth: 1, borderColor: C.border,
  },
  compTopRow: {
    flexDirection: 'row', gap: 14,
  },
  compLeft: {
    minWidth: 100,
  },
  compIcon: { width: 34, height: 34, borderRadius: 10, alignItems: 'center', justifyContent: 'center', marginBottom: 8 },
  compLabel: { color: C.textMuted, fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  compValue: { color: C.text, fontSize: 22, fontWeight: '800', marginTop: 2 },
  compDelta: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 3,
    borderRadius: 8, marginTop: 6,
  },
  compDeltaText: { fontSize: 11, fontWeight: '800' },
  compPrevLabel: { color: C.textMuted, fontSize: 10, marginTop: 6 },
  compBreakdown: {
    flex: 1,
    borderLeftWidth: 1, borderLeftColor: C.border + '60',
    paddingLeft: 12,
    justifyContent: 'center',
    gap: 3,
  },
  compBreakdownText: { color: C.textSec, fontSize: 12, lineHeight: 17 },
  compBreakdownDivider: { color: C.border, fontSize: 10, letterSpacing: -1 },

  // Cards
  card: {
    backgroundColor: C.surface, borderRadius: 16, padding: 18,
    borderWidth: 1, borderColor: C.border, marginBottom: 14,
  },
  sectionTitle: { color: C.text, fontSize: 16, fontWeight: '800', marginBottom: 2 },
  sectionSub: { color: C.textMuted, fontSize: 11, fontWeight: '600', marginBottom: 14 },
  noData: { color: C.textMuted, fontSize: 13, textAlign: 'center', paddingVertical: 30 },

  // Instructor revenue
  instrRow: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: C.border + '40',
  },
  instrInfo: { width: 100 },
  instrName: { color: C.text, fontSize: 13, fontWeight: '700' },
  instrMeta: { color: C.textMuted, fontSize: 10, marginTop: 1 },
  instrBarWrap: { flex: 1, height: 20, backgroundColor: C.surfaceHigh, borderRadius: 6, overflow: 'hidden' },
  instrBar: { height: '100%', borderRadius: 6 },
  instrAmount: { color: C.text, fontSize: 13, fontWeight: '800', width: 80, textAlign: 'right' },

  // Occupancy
  occRow: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: C.border + '40',
  },
  occName: { color: C.text, fontSize: 13, fontWeight: '700', width: 90 },
  occBarWrap: { flex: 1, height: 14, borderRadius: 7, overflow: 'hidden', position: 'relative' },
  occBarBg: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: C.surfaceHigh, borderRadius: 7,
  },
  occBarFill: { position: 'absolute', top: 0, left: 0, bottom: 0, borderRadius: 7 },
  occRank: { fontSize: 14, fontWeight: '800', width: 28, textAlign: 'center' },
  occPct: { fontSize: 11, fontWeight: '700', width: 50, textAlign: 'right' },
  occDetail: { color: C.text, fontSize: 13, fontWeight: '800', width: 45, textAlign: 'right' },

  // Legend
  legend: { color: C.textMuted, fontSize: 10, fontWeight: '600', fontStyle: 'italic', marginBottom: 12 },

  // Sport rows
  sportRow: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: C.border,
  },
  sportName: { color: C.text, fontSize: 13, fontWeight: '700', width: 90 },
  sportBarWrap: { flex: 1, height: 18, backgroundColor: C.surfaceHigh, borderRadius: 9, overflow: 'hidden' },
  sportBar: { height: '100%', backgroundColor: C.primary, borderRadius: 9 },
  sportPerH: { color: C.primary, fontSize: 14, fontWeight: '900', width: 75, textAlign: 'right' },
  sportMeta: { color: C.textMuted, fontSize: 10, fontWeight: '600', width: 70, textAlign: 'right' },

  // Profit summary
  profitSummary: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10,
    backgroundColor: C.successSoft, borderRadius: 14, padding: 16, marginBottom: 16,
  },
  profitSumItem: { alignItems: 'center' },
  profitSumLabel: { color: C.textMuted, fontSize: 10, fontWeight: '700', textTransform: 'uppercase', marginBottom: 2 },
  profitSumValue: { fontSize: 18, fontWeight: '900' },
  profitSumMinus: { color: C.textMuted, fontSize: 20, fontWeight: '300' },

  // Table
  tblHeader: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    paddingVertical: 8, paddingHorizontal: 4,
    borderBottomWidth: 2, borderBottomColor: C.border,
    backgroundColor: C.surfaceAlt,
  },
  tblH: { color: C.textMuted, fontSize: 9, fontWeight: '800', textTransform: 'uppercase', textAlign: 'center' },
  tblRow: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    paddingVertical: 8, paddingHorizontal: 4,
    borderBottomWidth: 1, borderBottomColor: C.border,
  },
  tblCell: { color: C.textSec, fontSize: 11, textAlign: 'center' },
  marginBadge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  marginText: { fontSize: 10, fontWeight: '800' },

  // Profit detail cards
  profitDetailCard: {
    backgroundColor: C.surfaceHigh, borderRadius: 12, padding: 12,
    alignItems: 'center', borderWidth: 1, borderColor: C.border,
  },
  profitDetailLabel: { color: C.textMuted, fontSize: 9, fontWeight: '700', textTransform: 'uppercase', marginTop: 4 },
  profitDetailValue: { color: C.text, fontSize: 16, fontWeight: '900', marginTop: 2 },
  profitDetailCost: { fontSize: 11, fontWeight: '700', marginTop: 2 },

  // Instructor detail
  instrDetailStat: {
    backgroundColor: C.surfaceHigh, borderRadius: 10, padding: 10,
    minWidth: 90, alignItems: 'center',
  },
  instrDetailLabel: { color: C.textMuted, fontSize: 9, fontWeight: '700', textTransform: 'uppercase', marginBottom: 3 },
  instrDetailValue: { color: C.text, fontSize: 16, fontWeight: '800' },
})
