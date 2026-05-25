import { isOwnerEmail } from '@/lib/owner'
import {
  ActivityIndicator,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import { useState, useMemo, useCallback, useEffect } from 'react'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useQuery } from '@tanstack/react-query'
import {
  format,
  startOfWeek,
  endOfWeek,
  startOfMonth,
  endOfMonth,
  subDays,
  parseISO,
} from 'date-fns'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import { C } from '@/constants/Colors'
import { trackPageView } from '@/lib/analytics'

// ─── Owner-only guard ─────────────────────────────────────────────────────


// ─── Types ────────────────────────────────────────────────────────────────

type DateRangeKey = 'today' | 'week' | 'month' | 'season2026' | 'season2025' | 'alltime' | 'custom'

interface RawBooking {
  id: string
  total_price: number
  currency: string
  booking_status: string
  payment_status: string
  service_name_snap: string
  instructor_snap: string | null
  duration_hours: number | null
  start_time: string | null
  end_time: string | null
  start_date: string
  persons: number
  customer_id: string | null
  customer_email: string
  location: string
  external_channel: string | null
  source: string | null
}

interface SportBreakdown {
  sport: string
  bookings: number
  instrHours: number
  custHours: number
  revenuePLN: number
  revenueEUR: number
  avgPerInstrH: number
  avgPerCustH: number
}

interface InstructorBreakdown {
  name: string
  bookings: number
  instrHours: number
  custHours: number
  revenuePLN: number
  revenueEUR: number
  avgPerInstrH: number
  avgPerCustH: number
}

interface AnalyticsData {
  totalRevenuePLN: number
  totalRevenueEUR: number
  paidRevenuePLN: number
  paidRevenueEUR: number
  unpaidRevenuePLN: number
  unpaidRevenueEUR: number
  instructorHours: number
  customerHours: number
  avgPricePerInstrHour: number
  avgPricePerCustHour: number
  bookingsCount: number
  uniqueCustomers: number
  cancelledCount: number
  totalForCancelRate: number
  sports: SportBreakdown[]
  instructors: InstructorBreakdown[]
  rawBookings: RawBooking[]
}

// ─── Sport extraction helper ──────────────────────────────────────────────

const SPORT_KEYWORDS = [
  'Kitesurfing',
  'Windsurfing',
  'Wing Foil',
  'Surfing',
  'Deskorolka',
  'Bosman',
  'SUP',
]

function extractSport(serviceName: string): string {
  if (!serviceName) return 'Inne'
  for (const kw of SPORT_KEYWORDS) {
    if (serviceName.toLowerCase().includes(kw.toLowerCase())) return kw
  }
  return 'Inne'
}

// ─── Duration helper ──────────────────────────────────────────────────────

function getDurationHours(b: RawBooking): number {
  if (b.duration_hours != null && b.duration_hours > 0) return b.duration_hours
  if (b.start_time && b.end_time) {
    const [sh, sm] = b.start_time.split(':').map(Number)
    const [eh, em] = b.end_time.split(':').map(Number)
    const diff = (eh * 60 + em - sh * 60 - sm) / 60
    return diff > 0 ? diff : 0
  }
  return 0
}

// ─── Date range helper ────────────────────────────────────────────────────

function getDateRange(key: DateRangeKey, customFrom?: string, customTo?: string) {
  const now = new Date()
  switch (key) {
    case 'today':
      return { from: format(now, 'yyyy-MM-dd'), to: format(now, 'yyyy-MM-dd'), seasonFilter: 'current' as const }
    case 'week':
      return {
        from: format(startOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd'),
        to: format(endOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd'),
        seasonFilter: 'current' as const,
      }
    case 'month':
      return {
        from: format(startOfMonth(now), 'yyyy-MM-dd'),
        to: format(endOfMonth(now), 'yyyy-MM-dd'),
        seasonFilter: 'current' as const,
      }
    case 'season2026':
      return { from: '2026-01-01', to: '2026-12-31', seasonFilter: 'current' as const }
    case 'season2025':
      return { from: '2025-01-01', to: '2025-12-31', seasonFilter: '2025' as const }
    case 'alltime':
      return { from: '2020-01-01', to: '2030-12-31', seasonFilter: 'all' as const }
    case 'custom':
      return { from: customFrom ?? '2026-01-01', to: customTo ?? format(now, 'yyyy-MM-dd'), seasonFilter: 'all' as const }
    default:
      return { from: '2026-01-01', to: '2026-12-31', seasonFilter: 'current' as const }
  }
}

// ─── Data fetching ────────────────────────────────────────────────────────

async function fetchAnalyticsData(
  dateFrom: string,
  dateTo: string,
  seasonFilter: 'current' | '2025' | 'all',
  location: string,
  sportFilter: string,
  instructorFilter: string,
  paymentFilter: string,
): Promise<AnalyticsData> {
  // Fetch all bookings (paginated — Supabase default limit is 1000)
  const allBookings: RawBooking[] = []
  let offset = 0
  const PAGE = 1000
  while (true) {
    let q = supabase
      .from('bookings')
      .select(
        'id, total_price, currency, booking_status, payment_status, service_name_snap, instructor_snap, duration_hours, start_time, end_time, start_date, persons, customer_id, customer_email, location, external_channel, source',
      )
      .gte('start_date', dateFrom)
      .lte('start_date', dateTo)
      .order('start_date', { ascending: false })
      .range(offset, offset + PAGE - 1)

    // Season filter
    if (seasonFilter === 'current') {
      q = q.or('external_channel.is.null,external_channel.neq.legacy_import')
    } else if (seasonFilter === '2025') {
      q = q.eq('external_channel', 'legacy_import')
    }
    // 'all' = no season filter

    // Location filter
    if (location !== 'both') {
      q = q.eq('location', location)
    }

    const { data, error } = await q
    if (error) throw error
    const page = (data ?? []) as RawBooking[]
    allBookings.push(...page)
    if (page.length < PAGE) break
    offset += PAGE
  }

  let bookings = allBookings

  // Apply client-side filters (sport, instructor, payment)
  if (sportFilter && sportFilter !== 'all') {
    bookings = bookings.filter((b) => extractSport(b.service_name_snap) === sportFilter)
  }
  if (instructorFilter && instructorFilter !== 'all') {
    bookings = bookings.filter((b) => (b.instructor_snap ?? 'Brak') === instructorFilter)
  }
  if (paymentFilter && paymentFilter !== 'all') {
    bookings = bookings.filter((b) => b.payment_status === paymentFilter)
  }

  // Exclude cancelled for most metrics (but keep for cancel rate)
  const totalForCancelRate = bookings.length
  const cancelledCount = bookings.filter((b) => b.booking_status === 'cancelled').length
  const active = bookings.filter((b) => b.booking_status !== 'cancelled')

  // Revenue
  const totalRevenuePLN = active.filter((b) => b.currency === 'PLN').reduce((s, b) => s + Number(b.total_price || 0), 0)
  const totalRevenueEUR = active.filter((b) => b.currency === 'EUR').reduce((s, b) => s + Number(b.total_price || 0), 0)
  const paidRevenuePLN = active.filter((b) => b.currency === 'PLN' && b.payment_status === 'paid').reduce((s, b) => s + Number(b.total_price || 0), 0)
  const paidRevenueEUR = active.filter((b) => b.currency === 'EUR' && b.payment_status === 'paid').reduce((s, b) => s + Number(b.total_price || 0), 0)
  const unpaidRevenuePLN = active.filter((b) => b.currency === 'PLN' && ['unpaid', 'deposit_paid'].includes(b.payment_status)).reduce((s, b) => s + Number(b.total_price || 0), 0)
  const unpaidRevenueEUR = active.filter((b) => b.currency === 'EUR' && ['unpaid', 'deposit_paid'].includes(b.payment_status)).reduce((s, b) => s + Number(b.total_price || 0), 0)

  // Hours — SEPARATED: instructor hours vs customer hours
  // instructor_hours = duration of each booking (1 instructor × Xh = Xh)
  // customer_hours = duration × persons (1h × 3 persons = 3 customer-hours)
  const instructorHours = active.reduce((s, b) => s + getDurationHours(b), 0)
  const customerHours = active.reduce((s, b) => s + getDurationHours(b) * (b.persons || 1), 0)
  const totalRevenue = totalRevenuePLN + totalRevenueEUR * 4.3 // approximate EUR->PLN for avg calc
  const avgPricePerInstrHour = instructorHours > 0 ? totalRevenue / instructorHours : 0
  const avgPricePerCustHour = customerHours > 0 ? totalRevenue / customerHours : 0

  // Unique customers
  const customerSet = new Set<string>()
  active.forEach((b) => {
    if (b.customer_id) customerSet.add(b.customer_id)
    else if (b.customer_email) customerSet.add(b.customer_email)
  })

  // Sport breakdown
  const sportMap = new Map<string, { bookings: number; instrH: number; custH: number; pln: number; eur: number }>()
  active.forEach((b) => {
    const sport = extractSport(b.service_name_snap)
    const entry = sportMap.get(sport) ?? { bookings: 0, instrH: 0, custH: 0, pln: 0, eur: 0 }
    const dur = getDurationHours(b)
    entry.bookings++
    entry.instrH += dur
    entry.custH += dur * (b.persons || 1)
    if (b.currency === 'PLN') entry.pln += Number(b.total_price || 0)
    else entry.eur += Number(b.total_price || 0)
    sportMap.set(sport, entry)
  })
  const sports: SportBreakdown[] = Array.from(sportMap.entries())
    .map(([sport, v]) => {
      const rev = v.pln + v.eur * 4.3
      return {
        sport,
        bookings: v.bookings,
        instrHours: Math.round(v.instrH * 10) / 10,
        custHours: Math.round(v.custH * 10) / 10,
        revenuePLN: v.pln,
        revenueEUR: v.eur,
        avgPerInstrH: v.instrH > 0 ? Math.round(rev / v.instrH) : 0,
        avgPerCustH: v.custH > 0 ? Math.round(rev / v.custH) : 0,
      }
    })
    .sort((a, b) => (b.revenuePLN + b.revenueEUR * 4.3) - (a.revenuePLN + a.revenueEUR * 4.3))

  // Instructor breakdown
  const instrMap = new Map<string, { bookings: number; instrH: number; custH: number; pln: number; eur: number }>()
  active.forEach((b) => {
    const name = b.instructor_snap ?? 'Brak przypisania'
    const entry = instrMap.get(name) ?? { bookings: 0, instrH: 0, custH: 0, pln: 0, eur: 0 }
    const dur = getDurationHours(b)
    entry.bookings++
    entry.instrH += dur
    entry.custH += dur * (b.persons || 1)
    if (b.currency === 'PLN') entry.pln += Number(b.total_price || 0)
    else entry.eur += Number(b.total_price || 0)
    instrMap.set(name, entry)
  })
  const instructors: InstructorBreakdown[] = Array.from(instrMap.entries())
    .map(([name, v]) => {
      const rev = v.pln + v.eur * 4.3
      return {
        name,
        bookings: v.bookings,
        instrHours: Math.round(v.instrH * 10) / 10,
        custHours: Math.round(v.custH * 10) / 10,
        revenuePLN: v.pln,
        revenueEUR: v.eur,
        avgPerInstrH: v.instrH > 0 ? Math.round(rev / v.instrH) : 0,
        avgPerCustH: v.custH > 0 ? Math.round(rev / v.custH) : 0,
      }
    })
    .sort((a, b) => b.bookings - a.bookings)

  return {
    totalRevenuePLN,
    totalRevenueEUR,
    paidRevenuePLN,
    paidRevenueEUR,
    unpaidRevenuePLN,
    unpaidRevenueEUR,
    instructorHours: Math.round(instructorHours * 10) / 10,
    customerHours: Math.round(customerHours * 10) / 10,
    avgPricePerInstrHour: Math.round(avgPricePerInstrHour),
    avgPricePerCustHour: Math.round(avgPricePerCustHour),
    bookingsCount: active.length,
    uniqueCustomers: customerSet.size,
    cancelledCount,
    totalForCancelRate,
    sports,
    instructors,
    rawBookings: active,
  }
}

// ─── CSV export ───────────────────────────────────────────────────────────

function generateCSV(data: AnalyticsData, rangeLabel: string): string {
  const lines: string[] = []

  // Header
  lines.push(`Raport FLH Panel — ${rangeLabel}`)
  lines.push(`Wygenerowano: ${format(new Date(), 'yyyy-MM-dd HH:mm')}`)
  lines.push('')

  // Summary
  lines.push('PODSUMOWANIE')
  lines.push(`Przychod PLN;${data.totalRevenuePLN}`)
  lines.push(`Przychod EUR;${data.totalRevenueEUR}`)
  lines.push(`Oplacone PLN;${data.paidRevenuePLN}`)
  lines.push(`Oplacone EUR;${data.paidRevenueEUR}`)
  lines.push(`Nieoplacone PLN;${data.unpaidRevenuePLN}`)
  lines.push(`Nieoplacone EUR;${data.unpaidRevenueEUR}`)
  lines.push(`Godziny instruktora;${data.instructorHours}`)
  lines.push(`Godziny kursantow;${data.customerHours}`)
  lines.push(`Sr. cena/h instruktora;${data.avgPricePerInstrHour}`)
  lines.push(`Sr. cena/h kursanta;${data.avgPricePerCustHour}`)
  lines.push(`Rezerwacje;${data.bookingsCount}`)
  lines.push(`Unikalnych klientow;${data.uniqueCustomers}`)
  lines.push(`Anulowane;${data.cancelledCount}`)
  lines.push(`Wskaznik anulacji;${data.totalForCancelRate > 0 ? Math.round((data.cancelledCount / data.totalForCancelRate) * 100) : 0}%`)
  lines.push('')

  // Sport breakdown
  lines.push('SPORT;Rezerwacje;Godz. instr.;Godz. kurs.;PLN;EUR;Sr./h instr.;Sr./h kurs.')
  data.sports.forEach((s) => {
    lines.push(`${s.sport};${s.bookings};${s.instrHours};${s.custHours};${s.revenuePLN};${s.revenueEUR};${s.avgPerInstrH};${s.avgPerCustH}`)
  })
  lines.push('')

  // Instructor breakdown
  lines.push('INSTRUKTOR;Rezerwacje;Godz. instr.;Godz. kurs.;PLN;EUR;Sr./h instr.;Sr./h kurs.')
  data.instructors.forEach((i) => {
    lines.push(`${i.name};${i.bookings};${i.instrHours};${i.custHours};${i.revenuePLN};${i.revenueEUR};${i.avgPerInstrH};${i.avgPerCustH}`)
  })
  lines.push('')

  // Raw bookings
  lines.push('ID;Data;Usluga;Instruktor;Klient;Osoby;Cena;Waluta;Status;Platnosc;Godziny')
  data.rawBookings.forEach((b) => {
    lines.push(
      `${b.id};${b.start_date};${b.service_name_snap};${b.instructor_snap ?? ''};${b.customer_email};${b.persons};${b.total_price};${b.currency};${b.booking_status};${b.payment_status};${getDurationHours(b)}`,
    )
  })

  return lines.join('\n')
}

function downloadCSV(csv: string, filename: string) {
  if (Platform.OS === 'web') {
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } else {
    // Native — use Sharing API
    try {
      const Sharing = require('expo-sharing')
      const FileSystem = require('expo-file-system')
      const path = FileSystem.documentDirectory + filename
      FileSystem.writeAsStringAsync(path, csv, { encoding: FileSystem.EncodingType.UTF8 }).then(() => {
        Sharing.shareAsync(path)
      })
    } catch {
      // Fallback: alert
      console.warn('Sharing not available on this platform')
    }
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────

function fmtMoney(pln: number, eur: number): string {
  const parts: string[] = []
  if (pln > 0) parts.push(`${pln.toLocaleString('pl-PL')} PLN`)
  if (eur > 0) parts.push(`${eur.toLocaleString('pl-PL')} EUR`)
  return parts.join(' + ') || '0 PLN'
}

function fmtMoneyShort(pln: number, eur: number): string {
  if (pln > 0 && eur > 0) return `${Math.round(pln / 1000)}k + ${Math.round(eur)}E`
  if (pln > 0) {
    if (pln >= 10000) return `${(pln / 1000).toFixed(1)}k PLN`
    return `${pln.toLocaleString('pl-PL')} PLN`
  }
  if (eur > 0) return `${eur.toLocaleString('pl-PL')} EUR`
  return '0 PLN'
}

// ─── Date Range Chips Config ──────────────────────────────────────────────

const DATE_RANGES: Array<{ key: DateRangeKey; label: string }> = [
  { key: 'today', label: 'Dzis' },
  { key: 'week', label: 'Ten tydzien' },
  { key: 'month', label: 'Ten miesiac' },
  { key: 'season2026', label: 'Sezon 2026' },
  { key: 'season2025', label: 'Sezon 2025' },
  { key: 'alltime', label: 'Wszystko' },
]

const PAYMENT_FILTERS = [
  { value: 'all', label: 'Wszystkie' },
  { value: 'paid', label: 'Oplacone' },
  { value: 'unpaid', label: 'Nieoplacone' },
  { value: 'deposit_paid', label: 'Zaliczka' },
]

// ─── SummaryCard ──────────────────────────────────────────────────────────

function SummaryCard({
  label,
  value,
  color,
  icon,
  sub,
}: {
  label: string
  value: string
  color: string
  icon: React.ComponentProps<typeof Ionicons>['name']
  sub?: string
}) {
  return (
    <View style={[st.summaryCard, { borderTopColor: color }]}>
      <View style={[st.summaryIconBg, { backgroundColor: color + '18' }]}>
        <Ionicons name={icon} size={16} color={color} />
      </View>
      <Text style={st.summaryLabel}>{label}</Text>
      <Text style={[st.summaryValue, { color }]}>{value}</Text>
      {sub ? <Text style={st.summarySub}>{sub}</Text> : null}
    </View>
  )
}

// ─── Analytics Screen ─────────────────────────────────────────────────────

export default function AnalyticsScreen() {
  const router = useRouter()
  const { session, selectedLocation, userRole } = useAuth()
  const userEmail = session?.user?.email?.toLowerCase() ?? ''

  useEffect(() => { trackPageView('analytics') }, [])

  // Owner/admin guard
  if (userRole !== 'admin' && !isOwnerEmail(userEmail, userRole)) {
    return (
      <View style={st.centered}>
        <Ionicons name="lock-closed-outline" size={48} color={C.textMuted} />
        <Text style={st.accessDenied}>Brak dostepu</Text>
        <Text style={st.accessDeniedSub}>Tylko wlasciciele maja dostep do analityki finansowej.</Text>
        <TouchableOpacity onPress={() => router.back()} style={st.backLinkBtn}>
          <Text style={st.backLinkText}>Wstecz</Text>
        </TouchableOpacity>
      </View>
    )
  }

  const [dateRange, setDateRange] = useState<DateRangeKey>('season2026')
  const [sportFilter, setSportFilter] = useState('all')
  const [instructorFilter, setInstructorFilter] = useState('all')
  const [paymentFilter, setPaymentFilter] = useState('all')
  const [showFilters, setShowFilters] = useState(false)
  const [sortCol, setSortCol] = useState<string>('bookings')
  const [sortAsc, setSortAsc] = useState(false)
  const toggleSort = (col: string) => { if (sortCol === col) setSortAsc(!sortAsc); else { setSortCol(col); setSortAsc(false) } }

  const range = useMemo(() => getDateRange(dateRange), [dateRange])

  const { data, isLoading, isError } = useQuery({
    queryKey: ['analytics', range.from, range.to, range.seasonFilter, selectedLocation, sportFilter, instructorFilter, paymentFilter],
    queryFn: () =>
      fetchAnalyticsData(range.from, range.to, range.seasonFilter, selectedLocation, sportFilter, instructorFilter, paymentFilter),
    staleTime: 30000,
  })

  // Extract available sports & instructors for filter chips
  const availableSports = useMemo(() => {
    if (!data) return []
    return data.sports.map((s) => s.sport)
  }, [data])

  const availableInstructors = useMemo(() => {
    if (!data) return []
    return data.instructors.map((i) => i.name)
  }, [data])

  const handleExportCSV = useCallback(() => {
    if (!data) return
    const rangeLabel = DATE_RANGES.find((r) => r.key === dateRange)?.label ?? dateRange
    const csv = generateCSV(data, rangeLabel)
    const filename = `flh-analytics-${format(new Date(), 'yyyy-MM-dd')}.csv`
    downloadCSV(csv, filename)
  }, [data, dateRange])

  const cancelRate = data && data.totalForCancelRate > 0
    ? Math.round((data.cancelledCount / data.totalForCancelRate) * 100)
    : 0

  return (
    <View style={st.root}>
      {/* Header */}
      <View style={st.header}>
        <TouchableOpacity onPress={() => router.back()} style={st.backBtn} activeOpacity={0.7}>
          <Ionicons name="chevron-back" size={20} color={C.textSec} />
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={st.headerTitle}>Finanse & Analityka</Text>
          <Text style={st.headerSub}>Przychody, godziny, statystyki</Text>
        </View>
        <TouchableOpacity onPress={handleExportCSV} style={st.exportBtn} activeOpacity={0.7} disabled={!data}>
          <Ionicons name="download-outline" size={16} color={data ? C.primary : C.textMuted} />
          <Text style={[st.exportBtnText, { color: data ? C.primary : C.textMuted }]}>CSV</Text>
        </TouchableOpacity>
      </View>

      {/* Date range chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={st.chipsScroll}
        contentContainerStyle={st.chipsContent}
      >
        {DATE_RANGES.map((r) => {
          const isActive = dateRange === r.key
          return (
            <TouchableOpacity
              key={r.key}
              onPress={() => setDateRange(r.key)}
              activeOpacity={0.7}
              style={[st.chip, isActive && st.chipActive]}
            >
              <Text style={[st.chipText, isActive && st.chipTextActive]}>{r.label}</Text>
            </TouchableOpacity>
          )
        })}
      </ScrollView>

      {/* Filter toggle */}
      <TouchableOpacity
        onPress={() => setShowFilters(!showFilters)}
        style={st.filterToggle}
        activeOpacity={0.7}
      >
        <Ionicons name="filter-outline" size={14} color={C.textSec} />
        <Text style={st.filterToggleText}>
          Filtry{showFilters ? '' : (sportFilter !== 'all' || instructorFilter !== 'all' || paymentFilter !== 'all') ? ' (aktywne)' : ''}
        </Text>
        <Ionicons name={showFilters ? 'chevron-up' : 'chevron-down'} size={14} color={C.textMuted} />
      </TouchableOpacity>

      {/* Filters panel */}
      {showFilters && (
        <View style={st.filterPanel}>
          {/* Payment status */}
          <Text style={st.filterLabel}>Platnosc</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={st.filterRow}>
              {PAYMENT_FILTERS.map((f) => (
                <TouchableOpacity
                  key={f.value}
                  onPress={() => setPaymentFilter(f.value)}
                  style={[st.filterChip, paymentFilter === f.value && st.filterChipActive]}
                  activeOpacity={0.7}
                >
                  <Text style={[st.filterChipText, paymentFilter === f.value && st.filterChipTextActive]}>
                    {f.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>

          {/* Sport */}
          {availableSports.length > 0 && (
            <>
              <Text style={st.filterLabel}>Sport</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                <View style={st.filterRow}>
                  <TouchableOpacity
                    onPress={() => setSportFilter('all')}
                    style={[st.filterChip, sportFilter === 'all' && st.filterChipActive]}
                    activeOpacity={0.7}
                  >
                    <Text style={[st.filterChipText, sportFilter === 'all' && st.filterChipTextActive]}>Wszystkie</Text>
                  </TouchableOpacity>
                  {availableSports.map((s) => (
                    <TouchableOpacity
                      key={s}
                      onPress={() => setSportFilter(s)}
                      style={[st.filterChip, sportFilter === s && st.filterChipActive]}
                      activeOpacity={0.7}
                    >
                      <Text style={[st.filterChipText, sportFilter === s && st.filterChipTextActive]}>{s}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </ScrollView>
            </>
          )}

          {/* Instructor */}
          {availableInstructors.length > 0 && (
            <>
              <Text style={st.filterLabel}>Instruktor</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                <View style={st.filterRow}>
                  <TouchableOpacity
                    onPress={() => setInstructorFilter('all')}
                    style={[st.filterChip, instructorFilter === 'all' && st.filterChipActive]}
                    activeOpacity={0.7}
                  >
                    <Text style={[st.filterChipText, instructorFilter === 'all' && st.filterChipTextActive]}>Wszyscy</Text>
                  </TouchableOpacity>
                  {availableInstructors.map((i) => (
                    <TouchableOpacity
                      key={i}
                      onPress={() => setInstructorFilter(i)}
                      style={[st.filterChip, instructorFilter === i && st.filterChipActive]}
                      activeOpacity={0.7}
                    >
                      <Text style={[st.filterChipText, instructorFilter === i && st.filterChipTextActive]}>{i}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </ScrollView>
            </>
          )}

          {/* Reset */}
          {(sportFilter !== 'all' || instructorFilter !== 'all' || paymentFilter !== 'all') && (
            <TouchableOpacity
              onPress={() => { setSportFilter('all'); setInstructorFilter('all'); setPaymentFilter('all') }}
              style={st.resetBtn}
              activeOpacity={0.7}
            >
              <Ionicons name="close-circle-outline" size={14} color={C.error} />
              <Text style={st.resetBtnText}>Resetuj filtry</Text>
            </TouchableOpacity>
          )}
        </View>
      )}

      {/* Content */}
      <ScrollView style={st.scroll} contentContainerStyle={st.scrollContent} showsVerticalScrollIndicator={true}>
        {isLoading ? (
          <ActivityIndicator color={C.primary} size="large" style={{ marginTop: 60 }} />
        ) : isError ? (
          <View style={st.errorBox}>
            <Ionicons name="alert-circle-outline" size={36} color={C.error} />
            <Text style={st.errorText}>Nie udalo sie zaladowac danych.</Text>
          </View>
        ) : data ? (
          <>
            {/* ── Summary Cards ──────────────────────────────────── */}
            <View style={st.summaryGrid}>
              <SummaryCard
                label="Przychod"
                value={fmtMoney(data.totalRevenuePLN, data.totalRevenueEUR)}
                color={C.primary}
                icon="cash-outline"
              />
              <SummaryCard
                label="Oplacone"
                value={fmtMoney(data.paidRevenuePLN, data.paidRevenueEUR)}
                color={C.success}
                icon="checkmark-circle-outline"
              />
              <SummaryCard
                label="Nieoplacone"
                value={fmtMoney(data.unpaidRevenuePLN, data.unpaidRevenueEUR)}
                color={data.unpaidRevenuePLN + data.unpaidRevenueEUR > 0 ? C.error : C.success}
                icon="alert-circle-outline"
              />
              <SummaryCard
                label="Godz. instruktora"
                value={`${data.instructorHours}h`}
                color="#7c3aed"
                icon="time-outline"
              />
              <SummaryCard
                label="Godz. kursantow"
                value={`${data.customerHours}h`}
                color="#a78bfa"
                icon="people-outline"
              />
              <SummaryCard
                label="Sr./h instruktora"
                value={data.avgPricePerInstrHour > 0 ? `${data.avgPricePerInstrHour} PLN` : '-'}
                color={C.accent}
                icon="trending-up-outline"
              />
              <SummaryCard
                label="Sr./h kursanta"
                value={data.avgPricePerCustHour > 0 ? `${data.avgPricePerCustHour} PLN` : '-'}
                color="#06b6d4"
                icon="trending-down-outline"
              />
              <SummaryCard
                label="Rezerwacje"
                value={String(data.bookingsCount)}
                color={C.primary}
                icon="clipboard-outline"
              />
              <SummaryCard
                label="Klienci"
                value={String(data.uniqueCustomers)}
                color={C.success}
                icon="people-outline"
              />
              <SummaryCard
                label="Anulacje"
                value={`${cancelRate}%`}
                color={cancelRate > 15 ? C.error : cancelRate > 5 ? C.warning : C.success}
                icon="close-circle-outline"
                sub={`${data.cancelledCount} z ${data.totalForCancelRate}`}
              />
            </View>

            {/* ── Sport Breakdown ────────────────────────────────── */}
            {data.sports.length > 0 && (
              <>
                <Text style={st.sectionTitle}>Podział wg sportu</Text>
                <View style={st.legendBox}>
                  <Text style={st.legendText}>📖 <Text style={st.legendBold}>Rez.</Text> = liczba rezerwacji · <Text style={st.legendBold}>H instr.</Text> = godziny pracy instruktora · <Text style={st.legendBold}>H kurs.</Text> = godziny × osoby (ile godzin klienci laczeni spedzili)</Text>
                  <Text style={st.legendText}>💰 <Text style={st.legendBold}>Przychod</Text> = suma oplaconych rezerwacji · <Text style={st.legendBold}>Sr./h i.</Text> = przychod / H instr. (ile zarabiamy za 1h instruktora) · <Text style={st.legendBold}>Sr./h k.</Text> = przychod / H kurs.</Text>
                </View>
                <ScrollView horizontal showsHorizontalScrollIndicator={true}>
                <View style={[st.tableCard, { minWidth: 500 }]}>
                  <View style={st.tableHeaderRow}>
                    {[
                      { key: 'sport', label: 'Sport', w: 110, align: 'left' },
                      { key: 'bookings', label: 'Rez.', w: 40, align: 'right' },
                      { key: 'instrHours', label: 'H instr.', w: 55, align: 'right' },
                      { key: 'custHours', label: 'H kurs.', w: 55, align: 'right' },
                      { key: 'revenuePLN', label: 'Przychod', w: 90, align: 'right' },
                      { key: 'avgPerInstrH', label: 'Sr./h i.', w: 60, align: 'right' },
                      { key: 'avgPerCustH', label: 'Sr./h k.', w: 60, align: 'right' },
                    ].map(col => (
                      <TouchableOpacity key={col.key} style={{ width: col.w }} onPress={() => toggleSort(col.key)} activeOpacity={0.6}>
                        <Text style={[st.tableHeaderCell, { textAlign: col.align as any }, sortCol === col.key && { color: '#0284c7' }]}>
                          {col.label}{sortCol === col.key ? (sortAsc ? ' ↑' : ' ↓') : ''}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                  {[...data.sports].sort((a: any, b: any) => {
                    const va = a[sortCol] ?? 0, vb = b[sortCol] ?? 0
                    if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va)
                    return sortAsc ? va - vb : vb - va
                  }).map((s, idx) => (
                    <View key={s.sport} style={[st.tableRow, idx % 2 === 0 && st.tableRowAlt]}>
                      <Text style={[st.tableCell, { width: 110, fontWeight: '600' }]} numberOfLines={1}>{s.sport}</Text>
                      <Text style={[st.tableCell, { width: 40, textAlign: 'right' }]}>{s.bookings}</Text>
                      <Text style={[st.tableCell, { width: 55, textAlign: 'right' }]}>{s.instrHours}</Text>
                      <Text style={[st.tableCell, { width: 55, textAlign: 'right' }]}>{s.custHours}</Text>
                      <Text style={[st.tableCell, { width: 90, textAlign: 'right', color: C.success, fontWeight: '600' }]}>
                        {fmtMoneyShort(s.revenuePLN, s.revenueEUR)}
                      </Text>
                      <Text style={[st.tableCell, { width: 60, textAlign: 'right' }]}>{s.avgPerInstrH || '-'}</Text>
                      <Text style={[st.tableCell, { width: 60, textAlign: 'right' }]}>{s.avgPerCustH || '-'}</Text>
                    </View>
                  ))}
                </View>
                </ScrollView>
              </>
            )}

            {/* ── Instructor Breakdown ──────────────────────────── */}
            {data.instructors.length > 0 && (
              <>
                <Text style={st.sectionTitle}>Podział wg instruktora</Text>
                <View style={st.legendBox}>
                  <Text style={st.legendText}>👨‍🏫 <Text style={st.legendBold}>Sr./h i.</Text> = ile klienci zaplacili za 1h pracy instruktora (przychod / H instr.)</Text>
                  <Text style={st.legendText}>💡 Np. Kondziu: 65.4k / 301.5h = <Text style={st.legendBold}>217 PLN/h</Text> — tyle klienci placa za jego godzine. Jesli stawka Kondzia = 100 PLN/h, to zysk = 217 − 100 = <Text style={st.legendBold}>117 PLN/h</Text></Text>
                  <Text style={st.legendText}>📊 Pelna analiza zyskownosci → <Text style={st.legendBold}>Raporty</Text> w menu (tabela z marza)</Text>
                </View>
                <ScrollView horizontal showsHorizontalScrollIndicator={true}>
                <View style={[st.tableCard, { minWidth: 500 }]}>
                  <View style={st.tableHeaderRow}>
                    {[
                      { key: 'name', label: 'Instruktor', w: 110, align: 'left' },
                      { key: 'bookings', label: 'Rez.', w: 40, align: 'right' },
                      { key: 'instrHours', label: 'H instr.', w: 55, align: 'right' },
                      { key: 'custHours', label: 'H kurs.', w: 55, align: 'right' },
                      { key: 'revenuePLN', label: 'Przychod', w: 90, align: 'right' },
                      { key: 'avgPerInstrH', label: 'Sr./h i.', w: 60, align: 'right' },
                      { key: 'avgPerCustH', label: 'Sr./h k.', w: 60, align: 'right' },
                    ].map(col => (
                      <TouchableOpacity key={col.key} style={{ width: col.w }} onPress={() => toggleSort(col.key)} activeOpacity={0.6}>
                        <Text style={[st.tableHeaderCell, { textAlign: col.align as any }, sortCol === col.key && { color: '#0284c7' }]}>
                          {col.label}{sortCol === col.key ? (sortAsc ? ' ↑' : ' ↓') : ''}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                  {[...data.instructors].sort((a: any, b: any) => {
                    const va = a[sortCol] ?? 0, vb = b[sortCol] ?? 0
                    if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va)
                    return sortAsc ? va - vb : vb - va
                  }).map((i, idx) => (
                    <View key={i.name} style={[st.tableRow, idx % 2 === 0 && st.tableRowAlt]}>
                      <Text style={[st.tableCell, { width: 110, fontWeight: '600' }]} numberOfLines={1}>{i.name}</Text>
                      <Text style={[st.tableCell, { width: 40, textAlign: 'right' }]}>{i.bookings}</Text>
                      <Text style={[st.tableCell, { width: 55, textAlign: 'right' }]}>{i.instrHours}</Text>
                      <Text style={[st.tableCell, { width: 55, textAlign: 'right' }]}>{i.custHours}</Text>
                      <Text style={[st.tableCell, { width: 90, textAlign: 'right', color: C.success, fontWeight: '600' }]}>
                        {fmtMoneyShort(i.revenuePLN, i.revenueEUR)}
                      </Text>
                      <Text style={[st.tableCell, { width: 60, textAlign: 'right' }]}>{i.avgPerInstrH || '-'}</Text>
                      <Text style={[st.tableCell, { width: 60, textAlign: 'right' }]}>{i.avgPerCustH || '-'}</Text>
                    </View>
                  ))}
                </View>
                </ScrollView>
              </>
            )}

            {/* ── Empty state ─────────────────────────────────── */}
            {data.bookingsCount === 0 && (
              <View style={st.emptyBox}>
                <Ionicons name="analytics-outline" size={48} color={C.border} />
                <Text style={st.emptyText}>Brak danych w wybranym zakresie</Text>
                <Text style={st.emptySub}>Zmien zakres dat lub filtry.</Text>
              </View>
            )}

            <View style={{ height: 40 }} />
          </>
        ) : null}
      </ScrollView>
    </View>
  )
}

// ─── Styles ───────────────────────────────────────────────────────────────

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },

  // Header
  header: {
    backgroundColor: C.surface,
    paddingTop: Platform.OS === 'web' ? 24 : 56,
    paddingBottom: 14,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: 12,
    backgroundColor: C.surfaceHigh,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: C.border,
  },
  headerTitle: { color: C.text, fontSize: 20, fontWeight: '800' },
  headerSub: { color: C.textMuted, fontSize: 12, marginTop: 1 },
  exportBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: C.primarySoft,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: C.primary + '30',
  },
  exportBtnText: { fontSize: 12, fontWeight: '700' },

  // Date range chips
  chipsScroll: { maxHeight: 48 },
  chipsContent: { paddingHorizontal: 20, paddingVertical: 10, gap: 8 },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.surface,
  },
  chipActive: {
    borderColor: C.primary,
    backgroundColor: C.primarySoft,
  },
  chipText: { color: C.textSec, fontSize: 12, fontWeight: '600' },
  chipTextActive: { color: C.primary, fontWeight: '700' },

  // Filter toggle
  filterToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 20,
    paddingVertical: 6,
  },
  filterToggleText: { color: C.textSec, fontSize: 12, fontWeight: '600' },

  // Filter panel
  filterPanel: {
    backgroundColor: C.surface,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
    paddingHorizontal: 20,
    paddingBottom: 12,
  },
  filterLabel: {
    color: C.textMuted,
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 8,
    marginBottom: 6,
  },
  filterRow: { flexDirection: 'row', gap: 6 },
  filterChip: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.surfaceHigh,
  },
  filterChipActive: {
    borderColor: C.primary,
    backgroundColor: C.primarySoft,
  },
  filterChipText: { color: C.textSec, fontSize: 11, fontWeight: '500' },
  filterChipTextActive: { color: C.primary, fontWeight: '700' },
  resetBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 10,
    alignSelf: 'flex-start',
  },
  resetBtnText: { color: C.error, fontSize: 11, fontWeight: '600' },

  // Scroll
  scroll: { flex: 1 },
  scrollContent: { padding: 20 },

  // Summary grid
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: 24,
  },
  summaryCard: {
    width: '48%' as any,
    backgroundColor: C.surface,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: C.border,
    borderTopWidth: 3,
  },
  summaryIconBg: {
    width: 28,
    height: 28,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  summaryLabel: { color: C.textMuted, fontSize: 11, fontWeight: '600', marginBottom: 4 },
  summaryValue: { fontSize: 16, fontWeight: '800' },
  summarySub: { color: C.textMuted, fontSize: 10, marginTop: 2 },

  // Section title
  sectionTitle: { color: C.text, fontSize: 16, fontWeight: '700', marginBottom: 12, marginTop: 4 },

  // Table
  tableCard: {
    backgroundColor: C.surface,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: C.border,
    overflow: 'hidden',
    marginBottom: 20,
  },
  tableHeaderRow: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: C.surfaceHigh,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  tableHeaderCell: {
    color: C.textMuted,
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
  tableRow: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: C.border + '40',
  },
  tableRowAlt: {
    backgroundColor: C.bg,
  },
  tableCell: {
    color: C.text,
    fontSize: 12,
  },

  // Legend
  legendBox: {
    backgroundColor: '#f8fafc',
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
    borderLeftWidth: 3,
    borderLeftColor: '#0284c7',
  },
  legendText: {
    color: '#64748b',
    fontSize: 11,
    lineHeight: 17,
    marginBottom: 3,
  },
  legendBold: {
    fontWeight: '800' as const,
    color: '#334155',
  },

  // Empty
  emptyBox: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: { color: C.textSec, fontSize: 16, fontWeight: '600', marginTop: 12 },
  emptySub: { color: C.textMuted, fontSize: 13, marginTop: 4 },

  // Error
  errorBox: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  errorText: { color: C.error, fontSize: 14, marginTop: 12 },

  // Access denied
  centered: {
    flex: 1,
    backgroundColor: C.bg,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  accessDenied: { color: C.text, fontSize: 18, fontWeight: '700', marginTop: 16 },
  accessDeniedSub: { color: C.textMuted, fontSize: 13, textAlign: 'center', marginTop: 6 },
  backLinkBtn: { marginTop: 20 },
  backLinkText: { color: C.primary, fontSize: 14, fontWeight: '600' },
})
