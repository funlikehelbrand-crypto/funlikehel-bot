import { isOwnerEmail } from '@/lib/owner'
import { useEffect } from 'react'
import {
  Image,
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Platform,
  ActivityIndicator,
  RefreshControl,
  useWindowDimensions,
} from 'react-native'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useAuth } from '@/contexts/AuthContext'
import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { format, startOfWeek, endOfWeek, startOfMonth, endOfMonth, addDays } from 'date-fns'
import { C, GRAD, getTheme } from '@/constants/Colors'
import { WindRose, degreesToCompass, isNorthSector } from '@/components/WindRose'
import { trackPageView } from '@/lib/analytics'
import { useLang, setLang, LANG_OPTIONS } from '@/lib/i18n'
import { TideWidget } from '@/components/TideWidget'

// ─── Data fetching ─────────────────────────────────────────────────────

async function fetchDashboardData(location: string) {
  const today = format(new Date(), 'yyyy-MM-dd')
  const now = new Date()
  const weekStart = format(startOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd')
  const weekEnd = format(endOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd')
  const monthStart = format(startOfMonth(now), 'yyyy-MM-dd')
  const monthEnd = format(endOfMonth(now), 'yyyy-MM-dd')

  const locFilter = location !== 'both' ? location : null

  // Today's lessons
  let todayQ = supabase
    .from('bookings')
    .select('id, booking_ref, customer_name, service_name_snap, start_time, end_time, instructor_snap, persons, booking_status, payment_status, total_price, currency')
    .eq('start_date', today)
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
    .order('start_time', { ascending: true })
  if (locFilter) todayQ = todayQ.eq('location', locFilter)
  const { data: todayBookings } = await todayQ

  // Pending bookings (all future)
  let pendingQ = supabase
    .from('bookings')
    .select('id, booking_ref, customer_name, service_name_snap, start_date, start_time, total_price, currency, payment_status')
    .eq('booking_status', 'pending')
    .gte('start_date', today)
    .or('external_channel.is.null,external_channel.neq.legacy_import')
    .order('start_date', { ascending: true })
    .limit(10)
  if (locFilter) pendingQ = pendingQ.eq('location', locFilter)
  const { data: pendingBookings } = await pendingQ

  // Unpaid bookings
  let unpaidQ = supabase
    .from('bookings')
    .select('total_price, currency')
    .in('payment_status', ['unpaid', 'deposit_paid'])
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
  if (locFilter) unpaidQ = unpaidQ.eq('location', locFilter)
  const { data: unpaidBookings } = await unpaidQ

  // Today's revenue (paid)
  let todayRevQ = supabase
    .from('bookings')
    .select('total_price, currency')
    .eq('start_date', today)
    .eq('payment_status', 'paid')
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
  if (locFilter) todayRevQ = todayRevQ.eq('location', locFilter)
  const { data: todayPaid } = await todayRevQ

  // This week revenue (paid)
  let weekQ = supabase
    .from('bookings')
    .select('total_price, currency')
    .gte('start_date', weekStart)
    .lte('start_date', weekEnd)
    .eq('payment_status', 'paid')
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
  if (locFilter) weekQ = weekQ.eq('location', locFilter)
  const { data: weekPaid } = await weekQ

  // This month revenue (paid)
  let monthQ = supabase
    .from('bookings')
    .select('total_price, currency')
    .gte('start_date', monthStart)
    .lte('start_date', monthEnd)
    .eq('payment_status', 'paid')
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
  if (locFilter) monthQ = monthQ.eq('location', locFilter)
  const { data: monthPaid } = await monthQ

  // Total all-time revenue
  let totalQ = supabase
    .from('bookings')
    .select('total_price, currency')
    .eq('payment_status', 'paid')
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
  if (locFilter) totalQ = totalQ.eq('location', locFilter)
  const { data: totalPaid } = await totalQ

  // Total customers & instructors
  let custQ = supabase.from('customers').select('id', { count: 'exact', head: true })
  const { count: customerCount } = await custQ

  let instrQ = supabase.from('instructors').select('id', { count: 'exact', head: true }).eq('is_active', true)
  const { count: instructorCount } = await instrQ

  // This week bookings count
  let weekCountQ = supabase
    .from('bookings')
    .select('id', { count: 'exact', head: true })
    .gte('start_date', weekStart)
    .lte('start_date', weekEnd)
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
  if (locFilter) weekCountQ = weekCountQ.eq('location', locFilter)
  const { count: weekBookingCount } = await weekCountQ

  // MEWIA transfers today
  let mewiaQ = supabase
    .from('bookings')
    .select('id, mewia_people_count, persons, mewia_status')
    .eq('start_date', today)
    .eq('mewia_transfer_required', true)
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
  if (locFilter) mewiaQ = mewiaQ.eq('location', locFilter)
  const { data: mewiaBookings } = await mewiaQ

  const mewiaPeople = (mewiaBookings ?? []).reduce((s: number, b: any) => s + (b.mewia_people_count || b.persons || 0), 0)
  const mewiaCount = (mewiaBookings ?? []).length

  // MEWIA transfers tomorrow
  const tomorrow = format(addDays(now, 1), 'yyyy-MM-dd')
  let mewiaTmrwQ = supabase
    .from('bookings')
    .select('id, mewia_people_count, persons')
    .eq('start_date', tomorrow)
    .eq('mewia_transfer_required', true)
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
  if (locFilter) mewiaTmrwQ = mewiaTmrwQ.eq('location', locFilter)
  const { data: mewiaTmrwBookings } = await mewiaTmrwQ

  const mewiaTmrwPeople = (mewiaTmrwBookings ?? []).reduce((s: number, b: any) => s + (b.mewia_people_count || b.persons || 0), 0)
  const mewiaTmrwCount = (mewiaTmrwBookings ?? []).length

  // MEWIA transfers this week (all days)
  let mewiaWeekQ = supabase
    .from('bookings')
    .select('id, start_date, mewia_people_count, persons, mewia_total_cost')
    .gte('start_date', weekStart)
    .lte('start_date', weekEnd)
    .eq('mewia_transfer_required', true)
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
  if (locFilter) mewiaWeekQ = mewiaWeekQ.eq('location', locFilter)
  const { data: mewiaWeekBookings } = await mewiaWeekQ

  const mewiaWeekPeople = (mewiaWeekBookings ?? []).reduce((s: number, b: any) => s + (b.mewia_people_count || b.persons || 0), 0)
  // Count unique days with transfers for fuel calc
  const mewiaWeekDaysSet = new Set((mewiaWeekBookings ?? []).map((b: any) => b.start_date))
  const mewiaWeekDaysWithTransfers = mewiaWeekDaysSet.size
  const mewiaWeekTrips = mewiaWeekDaysWithTransfers * 2 // tam + powrot per day
  const FUEL_PER_TRIP = 15
  const FUEL_PRICE = 8
  const mewiaWeekFuelL = mewiaWeekTrips * FUEL_PER_TRIP
  const mewiaWeekFuelCost = mewiaWeekFuelL * FUEL_PRICE
  const mewiaWeekRevenue = (mewiaWeekBookings ?? []).reduce((s: number, b: any) => s + (b.mewia_total_cost || (b.mewia_people_count || b.persons || 0) * 50), 0)

  // Today fuel
  const mewiaTodayTrips = mewiaCount > 0 ? 2 : 0
  const mewiaTodayFuelCost = mewiaTodayTrips * FUEL_PER_TRIP * FUEL_PRICE

  const sumPLN = (arr: any[] | null) => (arr ?? []).filter(b => b.currency === 'PLN').reduce((s, b) => s + Number(b.total_price || 0), 0)
  const sumEUR = (arr: any[] | null) => (arr ?? []).filter(b => b.currency === 'EUR').reduce((s, b) => s + Number(b.total_price || 0), 0)

  // Month instructor costs + revenue per hour
  const { data: instrRatesData } = await supabase.from('instructors').select('first_name, last_name, hourly_rate')
  const rateMap: Record<string, number> = {}
  for (const i of instrRatesData ?? []) {
    rateMap[`${i.first_name} ${i.last_name}`.trim()] = Number(i.hourly_rate) || 0
  }

  // This month bookings with hours for cost calc
  let monthBookQ = supabase
    .from('bookings')
    .select('instructor_snap, duration_hours, start_time, end_time, service_name_snap, total_price, currency, payment_status')
    .gte('start_date', monthStart)
    .lte('start_date', monthEnd)
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
  if (locFilter) monthBookQ = monthBookQ.eq('location', locFilter)
  const { data: monthBooks } = await monthBookQ

  let monthCost = 0
  let monthHours = 0
  for (const b of monthBooks ?? []) {
    let h = Number(b.duration_hours) || 0
    if (!h && b.start_time && b.end_time) {
      const [sh, sm] = b.start_time.split(':').map(Number)
      const [eh, em] = b.end_time.split(':').map(Number)
      h = Math.max(0, (eh * 60 + em - sh * 60 - sm) / 60)
    }
    monthHours += h
    const rate = rateMap[b.instructor_snap ?? ''] ?? 0
    if (rate > 0) {
      const isGroup = (b.service_name_snap ?? '').toLowerCase().includes('grupow') || (b.service_name_snap ?? '').toLowerCase().includes('podwójn')
      monthCost += h * (isGroup ? Math.round(rate * 1.15) : rate)
    }
  }

  const monthRevTotal = sumPLN(monthPaid) + sumEUR(monthPaid) * 4.3
  const monthProfit = monthRevTotal - monthCost
  const avgRevenuePerH = monthHours > 0 ? Math.round(monthRevTotal / monthHours) : 0
  const avgCostPerH = monthHours > 0 ? Math.round(monthCost / monthHours) : 0

  return {
    todayBookings: todayBookings ?? [],
    pendingBookings: pendingBookings ?? [],
    unpaidPLN: sumPLN(unpaidBookings),
    unpaidEUR: sumEUR(unpaidBookings),
    todayRevPLN: sumPLN(todayPaid),
    todayRevEUR: sumEUR(todayPaid),
    weekRevPLN: sumPLN(weekPaid),
    weekRevEUR: sumEUR(weekPaid),
    monthRevPLN: sumPLN(monthPaid),
    monthRevEUR: sumEUR(monthPaid),
    totalRevPLN: sumPLN(totalPaid),
    totalRevEUR: sumEUR(totalPaid),
    customerCount: customerCount ?? 0,
    instructorCount: instructorCount ?? 0,
    weekBookingCount: weekBookingCount ?? 0,
    mewiaPeople,
    mewiaCount,
    mewiaTmrwPeople,
    mewiaTmrwCount,
    mewiaWeekPeople,
    mewiaWeekTrips,
    mewiaWeekFuelL,
    mewiaWeekFuelCost,
    mewiaWeekRevenue,
    mewiaTodayTrips,
    mewiaTodayFuelCost,
    monthCost,
    monthProfit,
    monthHours,
    avgRevenuePerH,
    avgCostPerH,
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────

function fmtMoney(pln: number, eur: number): string {
  const parts: string[] = []
  if (pln > 0) parts.push(`${pln.toLocaleString('pl-PL')} PLN`)
  if (eur > 0) parts.push(`${eur.toLocaleString('pl-PL')} EUR`)
  return parts.join(' + ') || '0 PLN'
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#f59e0b', confirmed: '#0ea5e9', in_progress: '#22c55e',
  completed: '#475569', cancelled: '#ef4444',
}
const STATUS_PL: Record<string, string> = {
  pending: 'Oczekuje', confirmed: 'Potwierdzona', in_progress: 'W trakcie',
  completed: 'Zakonczona', unpaid: 'Nieoplacona', deposit_paid: 'Zaliczka', paid: 'Oplacona',
}

// ─── Tasks Summary Widget ──────────────────────────────────────────────

const TASK_PRIORITY_COLOR_DASH: Record<string, string> = {
  low: '#6b7280',
  medium: '#3b82f6',
  high: '#f59e0b',
  urgent: '#ef4444',
}

function TasksSummaryWidget() {
  const router = useRouter()
  const { selectedLocation, userRole } = useAuth()
  const { t } = useLang()

  // Only show for admin, staff, instructor
  if (userRole === 'customer') return null

  const { data: taskSummary } = useQuery({
    queryKey: ['tasks-summary', selectedLocation],
    queryFn: async () => {
      let q = supabase
        .from('tasks')
        .select('*')
        .in('status', ['pending', 'in_progress'])
      if (selectedLocation !== 'both') q = q.eq('location', selectedLocation)
      const { data, error } = await q
      if (error) throw error
      const today = new Date().toISOString().split('T')[0]
      const all = data ?? []
      const overdue = all.filter((t: any) => t.due_date && t.due_date < today)
      const priorityOrder: Record<string, number> = { urgent: 0, high: 1, medium: 2, low: 3 }
      const urgent = [...all].sort((a: any, b: any) => {
        return (priorityOrder[a.priority] ?? 3) - (priorityOrder[b.priority] ?? 3)
      }).slice(0, 3)
      return { total: all.length, overdue: overdue.length, top3: urgent }
    },
    staleTime: 60000,
  })

  if (!taskSummary) return null

  return (
    <>
      <View style={ds.sectionRow}>
        <Text style={ds.sectionTitle}>{t('tasks.title')}</Text>
        <TouchableOpacity onPress={() => router.push('/(app)/more/tasks' as any)}>
          <Text style={ds.seeAll}>Zobacz wszystkie →</Text>
        </TouchableOpacity>
      </View>

      {/* Count badges */}
      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 10 }}>
        <View style={{ backgroundColor: '#3b82f620', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: '#3b82f640' }}>
          <Text style={{ color: '#3b82f6', fontSize: 13, fontWeight: '700' }}>{taskSummary.total} aktywnych</Text>
        </View>
        {taskSummary.overdue > 0 && (
          <View style={{ backgroundColor: '#ef444420', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: '#ef444440' }}>
            <Text style={{ color: '#ef4444', fontSize: 13, fontWeight: '700' }}>{taskSummary.overdue} po terminie</Text>
          </View>
        )}
      </View>

      {/* Top 3 tasks */}
      {taskSummary.total === 0 ? (
        <View style={ds.emptyCard}>
          <Ionicons name="checkbox-outline" size={28} color={C.textMuted} />
          <Text style={ds.emptyTitle}>{t('tasks.noTasks')}</Text>
        </View>
      ) : (
        taskSummary.top3.map((task: any) => {
          const prioColor = TASK_PRIORITY_COLOR_DASH[task.priority] ?? C.textMuted
          const today = new Date().toISOString().split('T')[0]
          const isOverdue = task.due_date && task.due_date < today
          return (
            <TouchableOpacity
              key={task.id}
              style={ds.pendingCard}
              onPress={() => router.push('/(app)/more/tasks' as any)}
              activeOpacity={0.75}
            >
              <View style={[{ width: 4, borderRadius: 2, alignSelf: 'stretch', backgroundColor: prioColor }]} />
              <View style={{ flex: 1 }}>
                <Text style={ds.pendingName} numberOfLines={1}>{task.title}</Text>
                <View style={{ flexDirection: 'row', gap: 8, marginTop: 2 }}>
                  {task.assigned_to_name && (
                    <Text style={ds.pendingService} numberOfLines={1}>{task.assigned_to_name}</Text>
                  )}
                  {task.due_date && (
                    <Text style={[ds.pendingDate, isOverdue && { color: '#ef4444' }]}>
                      {isOverdue ? 'Po terminie: ' : ''}{task.due_date}
                    </Text>
                  )}
                </View>
              </View>
              <View style={{ backgroundColor: prioColor + '20', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2 }}>
                <Text style={{ color: prioColor, fontSize: 10, fontWeight: '700' }}>{task.priority}</Text>
              </View>
            </TouchableOpacity>
          )
        })
      )}
    </>
  )
}

// Styles for dashboard widget — reuse dashboard style object reference
const ds = StyleSheet.create({
  sectionRow: {
    flexDirection: 'row' as const, justifyContent: 'space-between' as const,
    alignItems: 'center' as const, marginBottom: 8, marginTop: 16,
  },
  sectionTitle: { color: C.text, fontSize: 16, fontWeight: '700' },
  seeAll: { color: C.primary, fontSize: 13, fontWeight: '600' },
  emptyCard: {
    backgroundColor: C.surface, borderRadius: 14, padding: 20,
    alignItems: 'center' as const, borderWidth: 1, borderColor: C.border, marginBottom: 8,
    flexDirection: 'row' as const, gap: 10,
  },
  emptyTitle: { color: C.textMuted, fontSize: 14 },
  pendingCard: {
    backgroundColor: C.surface, borderRadius: 12, marginBottom: 6,
    flexDirection: 'row' as const, alignItems: 'center' as const,
    padding: 12, borderWidth: 1, borderColor: C.border, gap: 10,
  },
  pendingName: { color: C.text, fontSize: 13, fontWeight: '600' },
  pendingService: { color: C.textMuted, fontSize: 11 },
  pendingDate: { color: C.textMuted, fontSize: 11 },
})

// ─── Instructor data fetching ─────────────────────────────────────────

interface WeatherData {
  temp: number
  windKn: number
  windDir: number
  weatherCode: number
}

const WEATHER_COORDS = {
  hel:      { lat: 54.6,  lon: 18.8 },
  hurghada: { lat: 27.26, lon: 33.81 },
}

interface DayForecast {
  date: string
  dayLabel: string
  tempMax: number
  tempMin: number
  weatherCode: number
  windKn: number
  windDir: number
}

interface WeatherDataExt extends WeatherData {
  waterTemp: number | null
  forecast7: DayForecast[]
}

async function fetchWeatherForLocation(location: string): Promise<WeatherDataExt> {
  const loc = location === 'hurghada' ? 'hurghada' : 'hel'
  const { lat, lon } = WEATHER_COORDS[loc]

  // Current weather + 7 day forecast
  const url =
    `https://api.open-meteo.com/v1/forecast` +
    `?latitude=${lat}&longitude=${lon}` +
    `&current=temperature_2m,wind_speed_10m,wind_direction_10m,weather_code` +
    `&daily=temperature_2m_max,temperature_2m_min,weather_code,wind_speed_10m_max,wind_direction_10m_dominant` +
    `&wind_speed_unit=kn&forecast_days=14&timezone=auto`

  const res = await fetch(url)
  if (!res.ok) throw new Error(`Open-Meteo error: ${res.status}`)
  const json = await res.json()
  const c = json.current
  const d = json.daily

  // Water temperature from Open-Meteo Marine API
  let waterTemp: number | null = null
  try {
    const marineUrl =
      `https://marine-api.open-meteo.com/v1/marine` +
      `?latitude=${lat}&longitude=${lon}` +
      `&current=sea_surface_temperature`
    const mRes = await fetch(marineUrl)
    if (mRes.ok) {
      const mJson = await mRes.json()
      waterTemp = mJson.current?.sea_surface_temperature ?? null
    }
  } catch {}

  // Parse 7-day forecast
  const DAY_NAMES = ['Nd', 'Pn', 'Wt', 'Sr', 'Cz', 'Pt', 'So']
  const forecast7: DayForecast[] = (d?.time ?? []).map((date: string, i: number) => ({
    date,
    dayLabel: DAY_NAMES[new Date(date).getDay()],
    tempMax: Math.round(d.temperature_2m_max[i]),
    tempMin: Math.round(d.temperature_2m_min[i]),
    weatherCode: d.weather_code[i],
    windKn: Math.round(d.wind_speed_10m_max?.[i] ?? 0),
    windDir: Math.round(d.wind_direction_10m_dominant?.[i] ?? 0),
  }))

  return {
    temp:        c.temperature_2m,
    windKn:      c.wind_speed_10m,
    windDir:     c.wind_direction_10m,
    weatherCode: c.weather_code,
    waterTemp,
    forecast7,
  }
}

async function fetchInstructorDashboard(userEmail: string, location: string) {
  const today = format(new Date(), 'yyyy-MM-dd')

  // Get instructor record by email
  const { data: instructor, error: instrErr } = await supabase
    .from('instructors')
    .select('id, first_name, last_name')
    .eq('email', userEmail)
    .single()

  if (instrErr || !instructor) {
    return { instructor: null, todayLessons: [], upcomingLessons: [], mewiaLessons: [] }
  }

  // Today's lessons
  const { data: todayLessons } = await supabase
    .from('bookings')
    .select('id, booking_ref, customer_name, service_name_snap, start_date, start_time, end_time, persons, booking_status, payment_status, total_price, currency, location, lesson_spot, mewia_transfer_required, mewia_people_count, mewia_total_cost, mewia_status, mewia_notes, customer:customers(first_name, last_name, skill_level, phone), service:services(name_en, category)')
    .eq('instructor_id', instructor.id)
    .eq('start_date', today)
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
    .order('start_time', { ascending: true })

  // Upcoming lessons (next 5, after today)
  const tomorrow = format(addDays(new Date(), 1), 'yyyy-MM-dd')
  const { data: upcomingLessons } = await supabase
    .from('bookings')
    .select('id, booking_ref, customer_name, service_name_snap, start_date, start_time, end_time, persons, booking_status, location, customer:customers(first_name, last_name, skill_level)')
    .eq('instructor_id', instructor.id)
    .gte('start_date', tomorrow)
    .neq('booking_status', 'cancelled')
    .or('external_channel.is.null,external_channel.neq.legacy_import')
    .order('start_date', { ascending: true })
    .order('start_time', { ascending: true })
    .limit(5)

  // MEWIA transfer lessons — today's lessons that require transfer
  const mewiaLessons = (todayLessons ?? []).filter(
    (l: any) => l.mewia_transfer_required === true
  )

  return {
    instructor,
    todayLessons: todayLessons ?? [],
    upcomingLessons: upcomingLessons ?? [],
    mewiaLessons,
  }
}

// ─── Weather info label ───────────────────────────────────────────────

function weatherLabel(code: number): string {
  if (code === 0)  return 'Bezchmurnie'
  if (code <= 2)   return 'Czesciowe zachmurzenie'
  if (code === 3)  return 'Zachmurzenie'
  if (code <= 49)  return 'Mgla'
  if (code <= 59)  return 'Mzawka'
  if (code <= 69)  return 'Deszcz'
  if (code <= 79)  return 'Snieg'
  if (code <= 84)  return 'Przelotny deszcz'
  return 'Burza'
}

function weatherIcon(code: number): React.ComponentProps<typeof Ionicons>['name'] {
  if (code === 0)  return 'sunny'
  if (code <= 2)   return 'partly-sunny'
  if (code === 3)  return 'cloudy'
  if (code <= 49)  return 'cloud'
  if (code <= 69)  return 'rainy'
  if (code <= 79)  return 'snow'
  if (code <= 84)  return 'rainy'
  return 'thunderstorm'
}

// ─── Instructor Dashboard Screen ──────────────────────────────────────

function InstructorDashboard() {
  const router = useRouter()
  const { session, selectedLocation } = useAuth()
  const userEmail = session?.user?.email ?? ''

  const today = new Date().toLocaleDateString('pl-PL', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['instructor-dashboard', userEmail, selectedLocation],
    queryFn: () => fetchInstructorDashboard(userEmail, selectedLocation),
    enabled: !!userEmail,
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
  })

  const { data: weather } = useQuery({
    queryKey: ['instructor-weather', selectedLocation],
    queryFn: () => fetchWeatherForLocation(selectedLocation),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  })

  const greeting = data?.instructor
    ? `Czesc, ${data.instructor.first_name}!`
    : 'Moje lekcje'

  return (
    <View style={ir.root}>
      {/* Header */}
      <View style={ir.header}>
        <Image source={require('@/assets/logo_flh02.png')} style={ir.headerLogo} resizeMode="contain" />
        <View style={{ flex: 1 }}>
          <Text style={ir.date}>{today}</Text>
          <Text style={ir.greeting}>{greeting}</Text>
        </View>
      </View>

      <ScrollView
        style={ir.scroll}
        contentContainerStyle={ir.scrollContent}
        showsVerticalScrollIndicator={true}
        refreshControl={
          <RefreshControl
            refreshing={isFetching && !isLoading}
            onRefresh={refetch}
            tintColor={C.primary}
          />
        }
      >
        {isLoading ? (
          <View style={ir.loadingBox}>
            <ActivityIndicator color={C.primary} size="large" />
          </View>
        ) : !data?.instructor ? (
          <View style={ir.emptyCard}>
            <Ionicons name="person-outline" size={36} color={C.textMuted} />
            <Text style={ir.emptyTitle}>Konto instruktora nie znalezione</Text>
            <Text style={ir.emptySubtitle}>
              Skontaktuj sie z administratorem, aby przypisac konto instruktora do Twojego emaila.
            </Text>
          </View>
        ) : (
          <>
            {/* ── Temperature ── */}
            {weather && (
              <View style={ir.weatherCard}>
                <View style={[ir.weatherTopRow, { marginBottom: 0 }]}>
                  <Ionicons name={weatherIcon(weather.weatherCode)} size={40} color={C.primary} />
                  <View style={ir.weatherInfo}>
                    <Text style={ir.weatherTemp}>{Math.round(weather.temp)}{'\u00B0'}C</Text>
                    <Text style={ir.weatherLabel}>{weatherLabel(weather.weatherCode)}</Text>
                  </View>
                </View>
              </View>
            )}

            {/* ── Tide / Water level ── */}
            <TideWidget location={selectedLocation} />
            <View style={{ height: 12 }} />

            {/* ── Wind + WindRose ── */}
            {weather && (
              <View style={ir.weatherCard}>
                <View style={ir.weatherTopRow}>
                  <Ionicons name="speedometer-outline" size={24} color={C.primary} />
                  <View style={ir.weatherInfo}>
                    <Text style={ir.weatherTemp}>{Math.round(weather.windKn)} kn</Text>
                    <Text style={ir.weatherLabel}>{degreesToCompass(weather.windDir)}</Text>
                  </View>
                </View>
                <WindRose degrees={weather.windDir} windKn={weather.windKn} />
              </View>
            )}

            {/* ── MEWIA transfer card (Zadanie 4) ── */}
            {data.mewiaLessons && data.mewiaLessons.length > 0 && (
              <>
                <View style={ir.sectionRow}>
                  <Text style={ir.sectionTitle}>Transfer MEWIA</Text>
                  <View style={ir.mewiaBadge}>
                    <Text style={ir.mewiaBadgeText}>{data.mewiaLessons.length}</Text>
                  </View>
                </View>
                {data.mewiaLessons.map((lesson: any) => {
                  const mStatusColor = MEWIA_STATUS_COLORS[lesson.mewia_status] ?? C.textMuted
                  return (
                    <TouchableOpacity
                      key={`mewia-${lesson.id}`}
                      style={ir.mewiaCard}
                      onPress={() => router.push(`/(app)/bookings/${lesson.id}` as any)}
                      activeOpacity={0.75}
                    >
                      <Ionicons name="boat-outline" size={20} color={C.warning} />
                      <View style={ir.mewiaCardInfo}>
                        <Text style={ir.mewiaCardCustomer}>{lesson.customer_name}</Text>
                        <Text style={ir.mewiaCardDetail}>
                          {lesson.mewia_people_count ?? lesson.persons} os. | {lesson.mewia_total_cost ?? 0} PLN
                        </Text>
                        <View style={[ir.mewiaStatusBadge, { backgroundColor: mStatusColor + '20' }]}>
                          <Text style={[ir.mewiaStatusText, { color: mStatusColor }]}>
                            {MEWIA_STATUS_LABELS[lesson.mewia_status] ?? lesson.mewia_status}
                          </Text>
                        </View>
                        {lesson.mewia_notes ? (
                          <Text style={ir.mewiaCardNotes}>{lesson.mewia_notes}</Text>
                        ) : null}
                      </View>
                      <Text style={ir.mewiaCardTime}>
                        {lesson.start_time?.slice(0, 5) ?? 'TBD'}
                      </Text>
                    </TouchableOpacity>
                  )
                })}
              </>
            )}

            {/* ── Today's lessons ── */}
            <View style={ir.sectionRow}>
              <Text style={ir.sectionTitle}>Moje lekcje dzis</Text>
              <Text style={ir.sectionCount}>{data.todayLessons.length}</Text>
            </View>

            {data.todayLessons.length === 0 ? (
              <View style={ir.emptyCard}>
                <Ionicons name="water-outline" size={36} color={C.primary} />
                <Text style={ir.emptyTitle}>Brak lekcji na dzis</Text>
                <Text style={ir.emptySubtitle}>Czas na treningi wlasne!</Text>
              </View>
            ) : (
              data.todayLessons.map((lesson: any) => {
                const customer = lesson.customer
                const skillColor = SKILL_COLORS[customer?.skill_level ?? ''] ?? C.textMuted
                return (
                  <TouchableOpacity
                    key={lesson.id}
                    style={ir.lessonCard}
                    onPress={() => router.push(`/(app)/bookings/${lesson.id}` as any)}
                    activeOpacity={0.75}
                  >
                    {/* Time column */}
                    <View style={ir.lessonTimeCol}>
                      <Text style={ir.lessonTimeText}>
                        {lesson.start_time?.slice(0, 5) ?? 'TBD'}
                      </Text>
                      {lesson.end_time && (
                        <Text style={ir.lessonTimeEnd}>{lesson.end_time.slice(0, 5)}</Text>
                      )}
                    </View>

                    {/* Divider */}
                    <View style={ir.lessonDivider} />

                    {/* Info */}
                    <View style={ir.lessonInfo}>
                      <Text style={ir.lessonCustomerName}>{lesson.customer_name}</Text>
                      <Text style={ir.lessonService}>{lesson.service_name_snap}</Text>
                      <View style={ir.lessonMetaRow}>
                        <Text style={ir.lessonMeta}>{lesson.persons} os.</Text>
                        <Text style={ir.lessonMeta}>
                          {lesson.location === 'hel' ? 'Hel' : 'Hurghada'}
                        </Text>
                        {customer?.skill_level && (
                          <View style={[ir.skillBadge, { backgroundColor: skillColor + '18' }]}>
                            <Text style={[ir.skillBadgeText, { color: skillColor }]}>
                              {customer.skill_level}
                            </Text>
                          </View>
                        )}
                      </View>
                      {customer?.phone && (
                        <Text style={ir.lessonPhone}>Tel: {customer.phone}</Text>
                      )}
                    </View>

                    {/* Status indicator */}
                    <View style={[ir.statusDot, { backgroundColor: STATUS_COLORS[lesson.booking_status] ?? C.textMuted }]} />
                  </TouchableOpacity>
                )
              })
            )}

            {/* ── Upcoming lessons ── */}
            {data.upcomingLessons.length > 0 && (
              <>
                <View style={ir.sectionRow}>
                  <Text style={ir.sectionTitle}>Nadchodzace lekcje</Text>
                  <TouchableOpacity onPress={() => router.push('/(app)/calendar' as any)}>
                    <Text style={ir.seeAllLink}>Kalendarz</Text>
                  </TouchableOpacity>
                </View>
                {data.upcomingLessons.map((lesson: any) => (
                  <TouchableOpacity
                    key={lesson.id}
                    style={ir.upcomingCard}
                    onPress={() => router.push(`/(app)/bookings/${lesson.id}` as any)}
                    activeOpacity={0.75}
                  >
                    <View style={ir.upcomingDateCol}>
                      <Text style={ir.upcomingDay}>
                        {format(new Date(lesson.start_date), 'EEE')}
                      </Text>
                      <Text style={ir.upcomingDate}>
                        {format(new Date(lesson.start_date), 'd MMM')}
                      </Text>
                    </View>
                    <View style={ir.upcomingDivider} />
                    <View style={ir.upcomingInfo}>
                      <Text style={ir.upcomingCustomer}>{lesson.customer_name}</Text>
                      <Text style={ir.upcomingService}>{lesson.service_name_snap}</Text>
                    </View>
                    <Text style={ir.upcomingTime}>
                      {lesson.start_time?.slice(0, 5) ?? 'TBD'}
                    </Text>
                  </TouchableOpacity>
                ))}
              </>
            )}

            <View style={{ height: 40 }} />
          </>
        )}
      </ScrollView>
    </View>
  )
}

const SKILL_COLORS: Record<string, string> = {
  beginner: '#22c55e',
  basic: '#0ea5e9',
  intermediate: '#f59e0b',
  advanced: '#a855f7',
  professional: '#ef4444',
}

const MEWIA_STATUS_COLORS: Record<string, string> = {
  not_required: '#94a3b8',
  required: '#f59e0b',
  confirmed: '#0ea5e9',
  paid: '#22c55e',
  cancelled: '#ef4444',
}

const MEWIA_STATUS_LABELS: Record<string, string> = {
  not_required: 'Nie wymagany',
  required: 'Wymagany',
  confirmed: 'Potwierdzony',
  paid: 'Oplacony',
  cancelled: 'Anulowany',
}

// ─── Customer data fetching ───────────────────────────────────────────

async function fetchCustomerDashboard(userEmail: string) {
  const today = format(new Date(), 'yyyy-MM-dd')

  // Upcoming bookings for this customer (by email)
  const { data: upcomingBookings } = await supabase
    .from('bookings')
    .select('id, booking_ref, service_name_snap, start_date, start_time, end_time, persons, booking_status, payment_status, total_price, currency, location')
    .eq('customer_email', userEmail)
    .gte('start_date', today)
    .neq('booking_status', 'cancelled')
    .order('start_date', { ascending: true })
    .limit(5)

  return {
    upcomingBookings: upcomingBookings ?? [],
  }
}

// ─── Customer Dashboard Screen ────────────────────────────────────────

function CustomerDashboard() {
  const router = useRouter()
  const { session, selectedLocation } = useAuth()
  const userEmail = session?.user?.email ?? ''

  const today = new Date().toLocaleDateString('pl-PL', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['customer-dashboard', userEmail],
    queryFn: () => fetchCustomerDashboard(userEmail),
    enabled: !!userEmail,
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
  })

  const { data: weather } = useQuery({
    queryKey: ['customer-weather', selectedLocation],
    queryFn: () => fetchWeatherForLocation(selectedLocation),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  })

  return (
    <View style={cr.root}>
      {/* Header */}
      <View style={cr.header}>
        <Image source={require('@/assets/logo_flh02.png')} style={cr.headerLogo} resizeMode="contain" />
        <View style={{ flex: 1 }}>
          <Text style={cr.date}>{today}</Text>
          <Text style={cr.greeting}>Witaj w FLH!</Text>
        </View>
      </View>

      <ScrollView
        style={cr.scroll}
        contentContainerStyle={cr.scrollContent}
        showsVerticalScrollIndicator={true}
        refreshControl={
          <RefreshControl
            refreshing={isFetching && !isLoading}
            onRefresh={refetch}
            tintColor={C.primary}
          />
        }
      >
        {/* ── Temperature ── */}
        {weather && (
          <View style={cr.weatherCard}>
            <View style={[cr.weatherTopRow, { marginBottom: 0 }]}>
              <Ionicons name={weatherIcon(weather.weatherCode)} size={40} color={C.primary} />
              <View style={cr.weatherInfo}>
                <Text style={cr.weatherTemp}>{Math.round(weather.temp)}{'\u00B0'}C</Text>
                <Text style={cr.weatherLabel}>{weatherLabel(weather.weatherCode)}</Text>
              </View>
            </View>
          </View>
        )}

        {/* ── Tide / Water level ── */}
        <View style={{ marginBottom: 16 }}>
          <TideWidget location={selectedLocation} />
        </View>

        {/* ── Wind + WindRose ── */}
        {weather && (
          <View style={cr.weatherCard}>
            <View style={cr.weatherTopRow}>
              <Ionicons name="speedometer-outline" size={24} color={C.primary} />
              <View style={cr.weatherInfo}>
                <Text style={cr.weatherTemp}>{Math.round(weather.windKn)} kn</Text>
                <Text style={cr.weatherLabel}>{degreesToCompass(weather.windDir)}</Text>
              </View>
            </View>
            <WindRose degrees={weather.windDir} windKn={weather.windKn} />
          </View>
        )}

        {/* ── Upcoming bookings ── */}
        <View style={cr.sectionRow}>
          <Text style={cr.sectionTitle}>Moje nadchodzące lekcje</Text>
          <TouchableOpacity onPress={() => router.push('/(app)/bookings' as any)}>
            <Text style={cr.seeAll}>Wszystkie →</Text>
          </TouchableOpacity>
        </View>

        {isLoading ? (
          <View style={cr.loadingBox}>
            <ActivityIndicator color={C.primary} size="large" />
          </View>
        ) : !data?.upcomingBookings.length ? (
          <View style={cr.emptyCard}>
            <Ionicons name="water-outline" size={36} color={C.primary} />
            <Text style={cr.emptyTitle}>Brak nadchodzących lekcji</Text>
            <Text style={cr.emptySubtitle}>Zarezerwuj swoją pierwszą lekcję!</Text>
          </View>
        ) : (
          data.upcomingBookings.map((booking: any) => (
            <View key={booking.id} style={cr.bookingCard}>
              <View style={cr.bookingDateCol}>
                <Text style={cr.bookingDay}>
                  {format(new Date(booking.start_date), 'EEE')}
                </Text>
                <Text style={cr.bookingDate}>
                  {format(new Date(booking.start_date), 'd MMM')}
                </Text>
              </View>
              <View style={cr.bookingDivider} />
              <View style={cr.bookingInfo}>
                <Text style={cr.bookingService}>{booking.service_name_snap}</Text>
                <View style={cr.bookingMetaRow}>
                  {booking.start_time && (
                    <Text style={cr.bookingMeta}>{booking.start_time.slice(0, 5)}</Text>
                  )}
                  <Text style={cr.bookingMeta}>{booking.persons} os.</Text>
                  <Text style={cr.bookingMeta}>
                    {booking.location === 'hel' ? 'Hel' : 'Hurghada'}
                  </Text>
                </View>
              </View>
              <View style={[cr.statusDot, {
                backgroundColor: STATUS_COLORS[booking.booking_status] ?? C.textMuted,
              }]} />
            </View>
          ))
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  )
}

// ─── Customer Dashboard Styles ─────────────────────────────────────────

const cr = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: {
    backgroundColor: C.surface,
    paddingTop: Platform.OS === 'web' ? 24 : 56,
    paddingBottom: 16, paddingHorizontal: 20,
    borderBottomWidth: 1, borderBottomColor: C.border,
    flexDirection: 'row' as const, alignItems: 'center' as const, gap: 14,
  },
  headerLogo: { width: 44, height: 44 },
  date: { color: C.textMuted, fontSize: 12, fontWeight: '500', marginBottom: 2 },
  greeting: { color: C.text, fontSize: 22, fontWeight: '800', letterSpacing: -0.5 },

  scroll: { flex: 1 },
  scrollContent: { padding: 20 },
  loadingBox: { paddingTop: 40, alignItems: 'center' as const },

  // Weather card (same as instructor)
  weatherCard: {
    backgroundColor: C.surface, borderRadius: 20, padding: 20,
    borderWidth: 1, borderColor: C.border, marginBottom: 16,
  },
  weatherTopRow: {
    flexDirection: 'row' as const, alignItems: 'center' as const, gap: 14, marginBottom: 16,
  },
  weatherInfo: { flex: 1 },
  weatherTemp: { color: C.text, fontSize: 32, fontWeight: '800' },
  weatherLabel: { color: C.textSec, fontSize: 13, fontWeight: '600' },
  weatherWindBadge: {
    alignItems: 'center' as const, backgroundColor: C.primarySoft,
    paddingHorizontal: 12, paddingVertical: 8, borderRadius: 12,
  },
  weatherWindValue: { color: C.primary, fontSize: 16, fontWeight: '800' },
  weatherWindDir: { color: C.primary, fontSize: 11, fontWeight: '600' },

  // Book CTA button
  bookBtn: {
    flexDirection: 'row' as const, alignItems: 'center' as const, justifyContent: 'center' as const,
    backgroundColor: C.primary, borderRadius: 16, paddingVertical: 16,
    gap: 10, marginBottom: 24,
  },
  bookBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },

  // Section headers
  sectionRow: {
    flexDirection: 'row' as const, justifyContent: 'space-between' as const,
    alignItems: 'center' as const, marginBottom: 12,
  },
  sectionTitle: { color: C.text, fontSize: 16, fontWeight: '700' },
  seeAll: { color: C.primary, fontSize: 13, fontWeight: '600' },

  // Empty state
  emptyCard: {
    backgroundColor: C.surface, borderRadius: 20, padding: 28,
    alignItems: 'center' as const, borderWidth: 1, borderColor: C.border, marginBottom: 20,
  },
  emptyTitle: { color: C.text, fontSize: 16, fontWeight: '700', marginBottom: 6, marginTop: 10 },
  emptySubtitle: { color: C.textMuted, fontSize: 13, textAlign: 'center' as const },

  // Upcoming booking cards
  bookingCard: {
    backgroundColor: C.surface, borderRadius: 14, marginBottom: 8,
    flexDirection: 'row' as const, alignItems: 'center' as const,
    padding: 12, borderWidth: 1, borderColor: C.border,
  },
  bookingDateCol: { width: 48, alignItems: 'center' as const },
  bookingDay: { color: C.primary, fontSize: 11, fontWeight: '600' },
  bookingDate: { color: C.text, fontSize: 12, fontWeight: '700' },
  bookingDivider: { width: 1, height: 36, backgroundColor: C.border, marginHorizontal: 12 },
  bookingInfo: { flex: 1 },
  bookingService: { color: C.text, fontSize: 13, fontWeight: '600', marginBottom: 4 },
  bookingMetaRow: { flexDirection: 'row' as const, gap: 10 },
  bookingMeta: { color: C.textMuted, fontSize: 11 },
  statusDot: { width: 10, height: 10, borderRadius: 5, marginLeft: 8 },
})

// ─── Admin / Staff Screen ────────────────────────────────────────────

// Owners who see full financial data

export default function DashboardScreen() {
  const router = useRouter()
  const { selectedLocation, userRole, session } = useAuth()
  const { width: screenWidth } = useWindowDimensions()
  const isMobile = screenWidth < 768
  const isOwner = isOwnerEmail(session?.user?.email, userRole)
  const { t, lang } = useLang()

  useEffect(() => { trackPageView('dashboard') }, [])

  // Instructor gets their own dashboard
  if (userRole === 'instructor') {
    return <InstructorDashboard />
  }

  // Customer gets their own simplified dashboard
  if (userRole === 'customer') {
    return <CustomerDashboard />
  }

  const today = new Date().toLocaleDateString('pl-PL', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard', selectedLocation],
    queryFn: () => fetchDashboardData(selectedLocation),
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
  })

  // Weather for MEWIA banner (admin)
  const { data: adminWeather } = useQuery({
    queryKey: ['admin-weather', selectedLocation],
    queryFn: () => fetchWeatherForLocation(selectedLocation),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  })

  const showMewiaBanner =
    adminWeather &&
    isNorthSector(adminWeather.windDir) &&
    (selectedLocation === 'hel' || selectedLocation === 'both')

  return (
    <View style={s.root}>
      {/* Header */}
      <View style={[s.header, Platform.OS === 'web' && { background: GRAD.header } as any]}>
        <Image source={require('@/assets/logo_flh02.png')} style={s.headerLogo} resizeMode="contain" />
        <View style={{ flex: 1 }}>
          <Text style={s.date}>{today}</Text>
          <Text style={s.title}>FLH Panel</Text>
        </View>
        <View style={s.headerRight}>
          <View style={s.headerBadge}>
            <Text style={{ fontSize: 14 }}>📍</Text>
            <Text style={s.headerBadgeText}>{selectedLocation === 'hel' ? 'Jastarnia' : selectedLocation === 'hurghada' ? 'Hurghada' : 'Oba'}</Text>
          </View>
        </View>
      </View>

      <ScrollView style={s.scroll} contentContainerStyle={s.scrollContent} showsVerticalScrollIndicator={true}>

        {isLoading ? (
          <View style={s.loadingBox}>
            <ActivityIndicator color={C.primary} size="large" />
          </View>
        ) : data ? (
          <>
            {/* ── KPI summary bar (owner only) ────────────────── */}
            {isOwner && (
              <TouchableOpacity
                style={[s.kpiBar, Platform.OS === 'web' && { background: GRAD.kpi } as any]}
                onPress={() => router.push('/(app)/more/reports' as any)}
                activeOpacity={0.8}
              >
                <View style={s.kpiItem}>
                  <Text style={s.kpiLabel}>{t('dash.hours_month')}</Text>
                  <Text style={s.kpiValue}>{Math.round(data.monthHours ?? 0)}h</Text>
                </View>
                <View style={s.kpiDivider} />
                <View style={s.kpiItem}>
                  <Text style={s.kpiLabel}>{t('dash.revenue')}</Text>
                  <Text style={[s.kpiValue, { color: '#4ade80' }]}>{fmtMoney(data.monthRevPLN, data.monthRevEUR)}</Text>
                </View>
                <View style={s.kpiDivider} />
                <View style={s.kpiItem}>
                  <Text style={s.kpiLabel}>{t('dash.instructor_cost')}</Text>
                  <Text style={[s.kpiValue, { color: '#fb923c' }]}>{data.monthCost > 0 ? `${Math.round(data.monthCost / 1000)}k` : '0'} PLN</Text>
                </View>
                <View style={s.kpiDivider} />
                <View style={s.kpiItem}>
                  <Text style={s.kpiLabel}>{t('dash.income')}</Text>
                  <Text style={[s.kpiValue, { color: data.monthProfit >= 0 ? '#4ade80' : '#f87171' }]}>{data.monthProfit > 0 ? `${Math.round(data.monthProfit / 1000)}k` : Math.round(data.monthProfit)} PLN</Text>
                </View>
                <View style={s.kpiDivider} />
                <View style={s.kpiItem}>
                  <Text style={s.kpiLabel}>{t('dash.avg_revenue_h')}</Text>
                  <Text style={s.kpiValue}>{data.avgRevenuePerH} PLN</Text>
                </View>
                <View style={s.kpiDivider} />
                <View style={s.kpiItem}>
                  <Text style={s.kpiLabel}>{t('dash.avg_cost_h')}</Text>
                  <Text style={[s.kpiValue, { color: '#fb923c' }]}>{data.avgCostPerH} PLN</Text>
                </View>
              </TouchableOpacity>
            )}

            {/* MEWIA banner moved below WindRose */}

            {/* ── Stats cards (mobile: on top, stacked; desktop: right column) ── */}
            {isMobile && (
              <View style={{ flexDirection: 'row', gap: 10, marginBottom: 16 }}>
                <TouchableOpacity
                  style={[s.statCard, { flex: 1 }, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(145deg, #0c4a6e 0%, #164e63 100%)' } as any]}
                  onPress={() => router.push('/(app)/calendar' as any)}
                  activeOpacity={0.75}
                >
                  <Text style={{ fontSize: 22, marginBottom: 2 }}>📋</Text>
                  <Text style={[s.statValue, { color: '#0369a1', fontSize: 22 }]}>{data.todayBookings.length}</Text>
                  <Text style={s.statLabel}>{t('dash.lessons_today')}</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[s.statCard, { flex: 1 }, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(145deg, #78350f 0%, #92400e 100%)' } as any]}
                  onPress={() => router.push('/(app)/bookings' as any)}
                  activeOpacity={0.75}
                >
                  <Text style={{ fontSize: 22, marginBottom: 2 }}>⏳</Text>
                  <Text style={[s.statValue, { color: '#b45309', fontSize: 22 }]}>{data.pendingBookings.length}</Text>
                  <Text style={s.statLabel}>{t('dash.pending')}</Text>
                </TouchableOpacity>
                {isOwner && <TouchableOpacity
                  style={[s.statCard, { flex: 1 }, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(145deg, #7f1d1d 0%, #991b1b 100%)' } as any]}
                  onPress={() => router.push('/(app)/more/payments' as any)}
                  activeOpacity={0.75}
                >
                  <Text style={{ fontSize: 22, marginBottom: 2 }}>💳</Text>
                  <Text style={[s.statValue, { color: '#dc2626', fontSize: 14 }]}>
                    {fmtMoney(data.unpaidPLN, data.unpaidEUR)}
                  </Text>
                  <Text style={s.statLabel}>{t('dash.to_pay')}</Text>
                </TouchableOpacity>}
              </View>
            )}

            {/* ── Weather + Stats — two columns on desktop ───── */}
            {!isMobile && (
            <View style={s.dashTopRow}>
              {/* LEFT: Weather + WindRose + wind scale */}
              {adminWeather && (
                <View style={[s.adminWeatherCard, Platform.OS === 'web' && { background: GRAD.card } as any]}>
                  {/* Decorative background emoji */}
                  <Text style={s.cardDecor}>🏖️</Text>
                  {/* ── Top row: Temp+badges LEFT | Tide chart RIGHT ── */}
                  <View style={s.adminWeatherTopRow}>
                    <View style={s.weatherIconCircle}>
                      <Text style={{ fontSize: 30 }}>{adminWeather.weatherCode === 0 ? '☀️' : adminWeather.weatherCode <= 2 ? '⛅' : adminWeather.weatherCode <= 3 ? '☁️' : adminWeather.weatherCode <= 69 ? '🌧️' : '⛈️'}</Text>
                    </View>
                    <View style={s.adminWeatherInfo}>
                      <Text style={s.adminWeatherTemp}>{Math.round(adminWeather.temp)}{'\u00B0'}C</Text>
                      <Text style={s.adminWeatherLabel}>{weatherLabel(adminWeather.weatherCode)}</Text>
                    </View>
                    {(adminWeather as any).waterTemp != null && (
                      <View style={[s.adminWeatherWindBadge, { backgroundColor: '#0ea5e918' }, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(135deg, #0c4a6e 0%, #0e7490 100%)' } as any]}>
                        <Text style={{ fontSize: 16 }}>🌊</Text>
                        <Text style={[s.adminWeatherWindValue, { color: '#0ea5e9' }]}>{Math.round((adminWeather as any).waterTemp)}{'\u00B0'}C</Text>
                        <Text style={s.adminWeatherWindDir}>woda</Text>
                      </View>
                    )}
                    <View style={[s.adminWeatherWindBadge, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(135deg, #0c4a6e 0%, #164e63 100%)' } as any]}>
                      <Text style={{ fontSize: 16 }}>💨</Text>
                      <Text style={s.adminWeatherWindValue}>{Math.round(adminWeather.windKn)} kn</Text>
                      <Text style={s.adminWeatherWindDir}>{degreesToCompass(adminWeather.windDir)}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <TideWidget location={selectedLocation} compact />
                    </View>
                  </View>

                  {/* ── Wind scale ── */}
                  <View style={{ flexDirection: 'row', gap: 3, alignItems: 'center', marginTop: 10, marginBottom: 6 }}>
                    {([
                      { r: '< 8', label: t('dash.too_weak'), color: C.textMuted, min: -1, max: 8 },
                      { r: '8-12', label: t('dash.learning'), color: C.warning, min: 8, max: 12 },
                      { r: '12-20', label: t('dash.ideal'), color: C.success, min: 12, max: 20 },
                      { r: '20-28', label: t('dash.advanced'), color: C.warning, min: 20, max: 28 },
                      { r: '> 28', label: t('dash.too_strong'), color: C.error, min: 28, max: 999 },
                    ]).map(row => {
                      const active = adminWeather.windKn >= row.min && adminWeather.windKn < row.max
                      return (
                        <View key={row.r} style={{ flex: 1, alignItems: 'center', paddingVertical: 6, paddingHorizontal: 4, backgroundColor: active ? row.color + '25' : 'transparent', borderRadius: 8, borderWidth: active ? 1 : 0, borderColor: row.color + '50' }}>
                          <Text style={{ color: row.color, fontSize: 12, fontWeight: '800' }}>{row.r}</Text>
                          <Text style={{ color: active ? row.color : C.textMuted, fontSize: 10, fontWeight: active ? '800' : '600', marginTop: 1 }}>{row.label}</Text>
                          {active && <Text style={{ color: row.color, fontSize: 9, fontWeight: '900', marginTop: 1 }}>{t('dash.now')}</Text>}
                        </View>
                      )
                    })}
                  </View>

                  {/* 14-day forecast — full width, flex wrap */}
                  {(adminWeather as any).forecast7?.length > 0 && (
                    <View style={{ marginTop: 10, marginBottom: 6 }}>
                      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 2 }}>
                        {((adminWeather as any).forecast7 as DayForecast[]).map((day, i) => {
                          const icon = day.weatherCode === 0 ? '☀️' : day.weatherCode <= 2 ? '⛅' : day.weatherCode <= 3 ? '☁️' : day.weatherCode <= 69 ? '🌧️' : '⛈️'
                          const windColor = day.windKn >= 12 ? '#22c55e' : day.windKn >= 8 ? '#f59e0b' : '#94a3b8'
                          return (
                            <View key={day.date} style={{ alignItems: 'center', paddingVertical: 5, paddingHorizontal: 2, backgroundColor: i === 0 ? C.primary + '15' : i % 2 === 0 ? 'rgba(255,255,255,0.03)' : 'transparent', borderRadius: 6, flex: 1, minWidth: 44 }}>
                              <Text style={{ color: i === 0 ? C.primary : C.textMuted, fontSize: 12, fontWeight: '800' }}>{day.dayLabel}</Text>
                              <Text style={{ fontSize: 14, marginVertical: 1 }}>{icon}</Text>
                              <Text style={{ color: C.text, fontSize: 12, fontWeight: '800' }}>{day.tempMax}{'\u00B0'}</Text>
                              <Text style={{ color: C.textMuted, fontSize: 12 }}>{day.tempMin}{'\u00B0'}</Text>
                              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 1, marginTop: 2 }}>
                                <Text style={{ color: windColor, fontSize: 11, fontWeight: '800' }}>{day.windKn}</Text>
                                <Text style={{ color: windColor, fontSize: 10 }}>kn</Text>
                              </View>
                              <Text style={{ color: windColor, fontSize: 13, fontWeight: '700', transform: [{ rotate: `${day.windDir}deg` }] }}>↓</Text>
                            </View>
                          )
                        })}
                      </View>
                    </View>
                  )}
                    {/* Wind rose + announcements side by side */}
                  <View style={s.roseAnnouncementsRow}>
                    <WindRose
                      degrees={adminWeather.windDir}
                      windKn={adminWeather.windKn}
                      hideSpotNote={selectedLocation === 'hurghada'}
                    />
                    <View style={s.announcementsBox}>
                      {/* Row 1: Messages + Bosman */}
                      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
                        {/* Messages */}
                        <TouchableOpacity
                          style={{ flex: 1, backgroundColor: '#06b6d415', borderRadius: 10, padding: 10, borderWidth: 1, borderColor: '#06b6d430' }}
                          onPress={() => router.push('/(app)/more/messages' as any)}
                          activeOpacity={0.8}
                        >
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 6 }}>
                            <Ionicons name="chatbubbles" size={14} color="#06b6d4" />
                            <Text style={{ color: '#06b6d4', fontSize: 12, fontWeight: '800', flex: 1 }}>{t('nav.messages')}</Text>
                            <View style={{ backgroundColor: '#ef4444', borderRadius: 8, paddingHorizontal: 5, paddingVertical: 1 }}>
                              <Text style={{ color: '#fff', fontSize: 11, fontWeight: '800' }}>7</Text>
                            </View>
                          </View>
                          <View style={{ gap: 4 }}>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                              <Ionicons name="logo-whatsapp" size={10} color="#25d366" />
                              <Text style={{ color: C.text, fontSize: 12, flex: 1 }} numberOfLines={1}>Klaus: Ich möchte einen Kurs buchen</Text>
                              <Text style={{ color: C.textMuted, fontSize: 10 }}>2m</Text>
                            </View>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                              <Ionicons name="logo-instagram" size={10} color="#E1306C" />
                              <Text style={{ color: C.text, fontSize: 12, flex: 1 }} numberOfLines={1}>Anna: Czy macie wolne terminy?</Text>
                              <Text style={{ color: C.textMuted, fontSize: 10 }}>15m</Text>
                            </View>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                              <Ionicons name="mail-outline" size={10} color="#6366f1" />
                              <Text style={{ color: C.text, fontSize: 12, flex: 1 }} numberOfLines={1}>Tomasz: Impreza firmowa 20 osób</Text>
                              <Text style={{ color: C.textMuted, fontSize: 10 }}>30m</Text>
                            </View>
                          </View>
                        </TouchableOpacity>

                        {/* Bosman */}
                        <TouchableOpacity
                          style={{ flex: 1, backgroundColor: '#f9731615', borderRadius: 10, padding: 10, borderWidth: 1, borderColor: '#f9731630' }}
                          onPress={() => router.push('/(app)/more/bosman' as any)}
                          activeOpacity={0.8}
                        >
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 6 }}>
                            <Ionicons name="hammer" size={14} color="#f97316" />
                            <Text style={{ color: '#f97316', fontSize: 12, fontWeight: '800', flex: 1 }}>Bosman</Text>
                            <View style={{ backgroundColor: '#ef4444', borderRadius: 8, paddingHorizontal: 5, paddingVertical: 1 }}>
                              <Text style={{ color: '#fff', fontSize: 11, fontWeight: '800' }}>4</Text>
                            </View>
                          </View>
                          <View style={{ gap: 3 }}>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                              <Ionicons name="flame" size={10} color="#ef4444" />
                              <Text style={{ color: C.text, fontSize: 12, flex: 1 }} numberOfLines={1}>Naprawic zagiel 7.0</Text>
                            </View>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                              <Ionicons name="arrow-up" size={10} color="#f97316" />
                              <Text style={{ color: C.text, fontSize: 12, flex: 1 }} numberOfLines={1}>Pompki — sprawdzic</Text>
                            </View>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                              <Ionicons name="arrow-up" size={10} color="#f97316" />
                              <Text style={{ color: C.text, fontSize: 12, flex: 1 }} numberOfLines={1}>Zamowic trapezy M i L</Text>
                            </View>
                          </View>
                        </TouchableOpacity>
                      </View>

                      {/* Row 2: MEWIA (full width) */}
                      {showMewiaBanner && data && (
                        <TouchableOpacity
                          style={{ backgroundColor: '#78350f40', borderRadius: 10, padding: 10, borderWidth: 1, borderColor: C.warning + '30', marginBottom: 8 }}
                          onPress={() => router.push('/(app)/more/mewia' as any)}
                          activeOpacity={0.8}
                        >
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 4 }}>
                            <Text style={{ fontSize: 14 }}>🚢</Text>
                            <Text style={{ color: C.warning, fontSize: 12, fontWeight: '800', flex: 1 }}>{t('dash.mewia_active')}</Text>
                            <Ionicons name="chevron-forward" size={12} color={C.warning} />
                          </View>
                          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                            <Text style={{ color: C.warning, fontSize: 12 }}>Dzis: {data.mewiaPeople} os. / {data.mewiaTodayTrips} rejsy</Text>
                            <Text style={{ color: C.warning, fontSize: 12 }}>Jutro: {data.mewiaTmrwPeople} os.</Text>
                            <Text style={{ color: C.warning, fontSize: 12 }}>Tydz: {data.mewiaWeekPeople} os.</Text>
                            <Text style={{ color: C.warning, fontSize: 12 }}>Paliwo: {data.mewiaWeekFuelL}L</Text>
                          </View>
                        </TouchableOpacity>
                      )}

                      <Text style={s.announcementTitle}>{t('dash.announcements')}</Text>
                      <View style={s.announcementItem}>
                        <Ionicons name="megaphone" size={15} color={C.warning} />
                        <View style={s.announcementContent}>
                          <Text style={s.announcementText}>Jutro zebranie o 7:00 — omowienie grafiku tygodnia</Text>
                          <Text style={s.announcementMeta}>Admin · dzis</Text>
                        </View>
                      </View>
                      <View style={s.announcementItem}>
                        <Ionicons name="information-circle" size={15} color={C.primary} />
                        <View style={s.announcementContent}>
                          <Text style={s.announcementText}>Nowy sprzet Cabrinha 2026 dostepny do testow od poniedzialku</Text>
                          <Text style={s.announcementMeta}>Admin · wczoraj</Text>
                        </View>
                      </View>
                    </View>
                  </View>

                  {/* Wind scale — inline */}
                  {/* Wind scale moved above forecast */}
                </View>
              )}

              {/* RIGHT: Stats cards — clickable, vertical stack */}
              <View style={s.statsCol}>
                <TouchableOpacity
                  style={[s.statCard, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(145deg, #0c4a6e 0%, #164e63 100%)' } as any]}
                  onPress={() => router.push('/(app)/calendar' as any)}
                  activeOpacity={0.75}
                >
                  <Text style={{ fontSize: 28, marginBottom: 4 }}>📋</Text>
                  <Text style={[s.statValue, { color: '#0369a1' }]}>{data.todayBookings.length}</Text>
                  <Text style={s.statLabel}>{t('dash.lessons_today')}</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[s.statCard, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(145deg, #78350f 0%, #92400e 100%)' } as any]}
                  onPress={() => router.push('/(app)/bookings' as any)}
                  activeOpacity={0.75}
                >
                  <Text style={{ fontSize: 28, marginBottom: 4 }}>⏳</Text>
                  <Text style={[s.statValue, { color: '#b45309' }]}>{data.pendingBookings.length}</Text>
                  <Text style={s.statLabel}>{t('dash.pending')}</Text>
                </TouchableOpacity>
                {isOwner && <TouchableOpacity
                  style={[s.statCard, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(145deg, #7f1d1d 0%, #991b1b 100%)' } as any]}
                  onPress={() => router.push('/(app)/more/payments' as any)}
                  activeOpacity={0.75}
                >
                  <Text style={{ fontSize: 28, marginBottom: 4 }}>💳</Text>
                  <Text style={[s.statValue, { color: '#dc2626', fontSize: data.unpaidPLN > 9999 ? 16 : 26 }]}>
                    {fmtMoney(data.unpaidPLN, data.unpaidEUR)}
                  </Text>
                  <Text style={s.statLabel}>{t('dash.to_pay')}</Text>
                </TouchableOpacity>}
              </View>
            </View>
            )}

            {/* TideWidget moved inside admin weather card (desktop) */}

            {/* ── Quick actions ────────────────────────────────── */}
            <Text style={s.sectionTitle}>{t('dash.quick_actions')}</Text>
            <View style={[s.actionsRow, isMobile && { flexWrap: 'wrap' }]}>
              {([
                { emoji: '➕', label: t('dash.new_booking'), bg: '#dbeafe', path: '/(app)/bookings/new' },
                { emoji: '📅', label: t('dash.calendar'), bg: '#ede9fe', path: '/(app)/calendar' },
                { emoji: '👥', label: t('dash.clients'), bg: '#dcfce7', path: '/(app)/people' },
                { emoji: '📋', label: t('nav.bookings'), bg: '#fef3c7', path: '/(app)/bookings' },
                { emoji: '💰', label: t('nav.finances'), bg: '#d1fae5', path: '/(app)/finances' },
                { emoji: '🪁', label: t('nav.equipment'), bg: '#e0f2fe', path: '/(app)/more/equipment' },
              ]).map((a) => (
                <TouchableOpacity key={a.path} style={s.action} onPress={() => router.push(a.path as any)} activeOpacity={0.75}>
                  <View style={[s.actionIcon, { backgroundColor: a.bg }]}>
                    <Text style={s.actionEmoji}>{a.emoji}</Text>
                  </View>
                  <Text style={s.actionLabel}>{a.label}</Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* ── Today's lessons ──────────────────────────────── */}
            <View style={s.sectionRow}>
              <Text style={s.sectionTitle}>{t('dash.today_lessons')}</Text>
              <TouchableOpacity onPress={() => router.push('/(app)/calendar' as any)}>
                <Text style={s.seeAll}>{t('dash.calendar_arrow')}</Text>
              </TouchableOpacity>
            </View>
            {data.todayBookings.length === 0 ? (
              <View style={s.emptyCard}>
                <Ionicons name="water-outline" size={36} color={C.primary} />
                <Text style={s.emptyTitle}>{t('cal.no_lessons')}</Text>
                <TouchableOpacity style={s.emptyBtn} onPress={() => router.push('/(app)/bookings/new' as any)}>
                  <Text style={s.emptyBtnText}>{t('dash.new_booking_btn')}</Text>
                </TouchableOpacity>
              </View>
            ) : (
              data.todayBookings.map((b: any) => (
                <TouchableOpacity
                  key={b.id}
                  style={s.lessonCard}
                  onPress={() => router.push(`/(app)/bookings/${b.id}` as any)}
                  activeOpacity={0.75}
                >
                  <View style={[s.lessonBar, { backgroundColor: STATUS_COLORS[b.booking_status] ?? C.textSec }]} />
                  <View style={s.lessonTime}>
                    <Text style={s.lessonTimeText}>{b.start_time?.slice(0, 5) ?? 'TBD'}</Text>
                    {b.end_time && <Text style={s.lessonTimeEnd}>{b.end_time.slice(0, 5)}</Text>}
                  </View>
                  <View style={s.lessonInfo}>
                    <Text style={s.lessonCustomer}>{b.customer_name}</Text>
                    <Text style={s.lessonService}>{b.service_name_snap}</Text>
                    <View style={s.lessonMeta}>
                      {b.instructor_snap && (
                        <View style={s.lessonMetaItem}>
                          <Ionicons name="person-outline" size={12} color={C.textMuted} />
                          <Text style={s.lessonMetaText}>{b.instructor_snap}</Text>
                        </View>
                      )}
                      <View style={s.lessonMetaItem}>
                        <Ionicons name="people-outline" size={12} color={C.textMuted} />
                        <Text style={s.lessonMetaText}>{b.persons}</Text>
                      </View>
                      <Text style={[s.lessonPayment, {
                        color: b.payment_status === 'paid' ? C.success : b.payment_status === 'unpaid' ? C.error : C.warning
                      }]}>
                        {STATUS_PL[b.payment_status] ?? b.payment_status}
                      </Text>
                    </View>
                  </View>
                  <Text style={s.lessonPrice}>{b.total_price} {b.currency}</Text>
                </TouchableOpacity>
              ))
            )}

            {/* ── Pending bookings ─────────────────────────────── */}
            {data.pendingBookings.length > 0 && (
              <>
                <View style={s.sectionRow}>
                  <Text style={s.sectionTitle}>Wymaga potwierdzenia</Text>
                  <View style={s.badgeWarn}><Text style={s.badgeWarnText}>{data.pendingBookings.length}</Text></View>
                </View>
                {data.pendingBookings.map((b: any) => (
                  <TouchableOpacity
                    key={b.id}
                    style={s.pendingCard}
                    onPress={() => router.push(`/(app)/bookings/${b.id}` as any)}
                    activeOpacity={0.75}
                  >
                    <View style={s.pendingLeft}>
                      <Text style={s.pendingName}>{b.customer_name}</Text>
                      <Text style={s.pendingService}>{b.service_name_snap}</Text>
                      <Text style={s.pendingDate}>{b.start_date} {b.start_time?.slice(0, 5)}</Text>
                    </View>
                    <View style={s.pendingRight}>
                      <Text style={s.pendingPrice}>{b.total_price} {b.currency}</Text>
                      <View style={s.pendingBadge}><Text style={s.pendingBadgeText}>Oczekuje</Text></View>
                    </View>
                  </TouchableOpacity>
                ))}
              </>
            )}

            {/* ── Tasks summary ────────────────────────────── */}
            <TasksSummaryWidget />

            {/* ── Financial summary ─────────────────────────── */}
            {isOwner ? (
              <>
                <TouchableOpacity onPress={() => router.push('/(app)/finances' as any)} activeOpacity={0.75}>
                  <View style={s.sectionRow}>
                    <Text style={s.sectionTitle}>{t('nav.finances')}</Text>
                    <Text style={s.seeAll}>{t('cal.details')} →</Text>
                  </View>
                </TouchableOpacity>
                <View style={[s.financeGrid, isMobile && { flexDirection: 'column' }]}>
                  <View style={[s.finCard, isMobile && { width: '100%' as any }, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(135deg, #14532d 0%, #166534 100%)' } as any]}>
                    <Text style={s.finCardEmoji}>💵</Text>
                    <Text style={s.finLabel}>{t('dash.revenue_month')}</Text>
                    <Text style={[s.finValue, { color: '#059669' }]}>{fmtMoney(data.monthRevPLN, data.monthRevEUR)}</Text>
                  </View>
                  <View style={[s.finCard, isMobile && { width: '100%' as any }, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%)' } as any]}>
                    <Text style={s.finCardEmoji}>👨‍🏫</Text>
                    <Text style={s.finLabel}>{t('dash.instructor_cost')}</Text>
                    <Text style={[s.finValue, { color: '#dc2626' }]}>{data.monthCost > 0 ? `${Math.round(data.monthCost / 1000)}k PLN` : '0 PLN'}</Text>
                  </View>
                  <View style={[s.finCard, isMobile && { width: '100%' as any }, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(135deg, #14532d 0%, #15803d 100%)' } as any]}>
                    <Text style={s.finCardEmoji}>📈</Text>
                    <Text style={s.finLabel}>{t('dash.income_month')}</Text>
                    <Text style={[s.finValue, { color: data.monthProfit >= 0 ? '#059669' : '#dc2626' }]}>{data.monthProfit > 0 ? `${Math.round(data.monthProfit / 1000)}k PLN` : `${Math.round(data.monthProfit)} PLN`}</Text>
                  </View>
                  <View style={[s.finCard, isMobile && { width: '100%' as any }, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(135deg, #0c4a6e 0%, #164e63 100%)' } as any]}>
                    <Text style={s.finCardEmoji}>⏱️</Text>
                    <Text style={s.finLabel}>{t('dash.revenue_per_h')}</Text>
                    <Text style={[s.finValue, { color: '#0369a1' }]}>{data.avgRevenuePerH} PLN</Text>
                  </View>
                  <View style={[s.finCard, isMobile && { width: '100%' as any }, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(135deg, #78350f 0%, #a16207 100%)' } as any]}>
                    <Text style={s.finCardEmoji}>💰</Text>
                    <Text style={s.finLabel}>{t('dash.avg_cost_h')}</Text>
                    <Text style={[s.finValue, { color: '#b45309' }]}>{data.avgCostPerH} PLN</Text>
                  </View>
                  <View style={[s.finCard, isMobile && { width: '100%' as any }, Platform.OS === 'web' && getTheme() === 'dark' && { background: data.unpaidPLN + data.unpaidEUR > 0 ? 'linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%)' : 'linear-gradient(135deg, #14532d 0%, #166534 100%)' } as any]}>
                    <Text style={s.finCardEmoji}>{data.unpaidPLN + data.unpaidEUR > 0 ? '⚠️' : '✅'}</Text>
                    <Text style={s.finLabel}>{t('fin.arrears')}</Text>
                    <Text style={[s.finValue, { color: data.unpaidPLN + data.unpaidEUR > 0 ? '#dc2626' : '#059669' }]}>
                      {data.unpaidPLN + data.unpaidEUR > 0 ? fmtMoney(data.unpaidPLN, data.unpaidEUR) : t('fin.no_arrears')}
                    </Text>
                  </View>
                </View>
              </>
            ) : (data.unpaidPLN + data.unpaidEUR > 0) ? (
              <View style={s.financeGrid}>
                <View style={[s.finCard, { width: '100%' as any }]}>
                  <Text style={s.finLabel}>Zaleglosci</Text>
                  <Text style={[s.finValue, { color: C.error }]}>
                    {fmtMoney(data.unpaidPLN, data.unpaidEUR)}
                  </Text>
                </View>
              </View>
            ) : null}

            {/* ── Team & clients ─────────────────────────────── */}
            <View style={s.teamRow}>
              <TouchableOpacity style={[s.teamCard, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(135deg, #0c4a6e 0%, #164e63 100%)' } as any]} onPress={() => router.push('/(app)/people' as any)} activeOpacity={0.75}>
                <Text style={{ fontSize: 32, marginBottom: 8 }}>👥</Text>
                <Text style={s.teamValue}>{data.customerCount}</Text>
                <Text style={s.teamLabel}>Klientow</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[s.teamCard, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(135deg, #14532d 0%, #166534 100%)' } as any]} onPress={() => router.push('/(app)/people' as any)} activeOpacity={0.75}>
                <Text style={{ fontSize: 32, marginBottom: 8 }}>🏄‍♂️</Text>
                <Text style={s.teamValue}>{data.instructorCount}</Text>
                <Text style={s.teamLabel}>Instruktorow</Text>
              </TouchableOpacity>
            </View>

            {/* ── Weather (mobile only — at the bottom) ─────── */}
            {isMobile && adminWeather && (
              <View style={[s.adminWeatherCard, { marginBottom: 16 }, Platform.OS === 'web' && { background: GRAD.card } as any]}>
                <Text style={s.cardDecor}>🏖️</Text>
                <View style={s.adminWeatherTopRow}>
                  <View style={s.weatherIconCircle}>
                    <Text style={{ fontSize: 30 }}>{adminWeather.weatherCode === 0 ? '☀️' : adminWeather.weatherCode <= 2 ? '⛅' : adminWeather.weatherCode <= 3 ? '☁️' : adminWeather.weatherCode <= 69 ? '🌧️' : '⛈️'}</Text>
                  </View>
                  <View style={s.adminWeatherInfo}>
                    <Text style={s.adminWeatherTemp}>{Math.round(adminWeather.temp)}{'\u00B0'}C</Text>
                    <Text style={s.adminWeatherLabel}>{weatherLabel(adminWeather.weatherCode)}</Text>
                  </View>
                  <View style={[s.adminWeatherWindBadge, Platform.OS === 'web' && getTheme() === 'dark' && { background: 'linear-gradient(135deg, #0c4a6e 0%, #164e63 100%)' } as any]}>
                    <Text style={{ fontSize: 16 }}>💨</Text>
                    <Text style={s.adminWeatherWindValue}>{Math.round(adminWeather.windKn)} kn</Text>
                    <Text style={s.adminWeatherWindDir}>{degreesToCompass(adminWeather.windDir)}</Text>
                  </View>
                </View>
                {/* Tide / Water level — between temp and wind */}
                <View style={{ marginVertical: 10 }}>
                  <TideWidget location={selectedLocation} compact />
                </View>
                <WindRose
                  degrees={adminWeather.windDir}
                  windKn={adminWeather.windKn}
                  hideSpotNote={selectedLocation === 'hurghada'}
                />
                <View style={s.windScaleSection}>
                  <Text style={s.windScaleTitle}>{t('dash.wind_assessment')}</Text>
                  {([
                    { range: '< 8 kn', label: t('dash.too_weak'), color: C.textMuted, icon: 'close-circle-outline' as const },
                    { range: '8-12 kn', label: t('dash.learning'), color: C.warning, icon: 'school-outline' as const },
                    { range: '12-20 kn', label: t('dash.ideal'), color: C.success, icon: 'checkmark-circle-outline' as const },
                    { range: '20-28 kn', label: t('dash.advanced'), color: C.warning, icon: 'alert-circle-outline' as const },
                    { range: '> 28 kn', label: t('dash.too_strong'), color: C.error, icon: 'close-circle-outline' as const },
                  ]).map((row) => {
                    const kn = adminWeather.windKn
                    const active =
                      (row.range === '< 8 kn' && kn < 8) ||
                      (row.range === '8-12 kn' && kn >= 8 && kn < 12) ||
                      (row.range === '12-20 kn' && kn >= 12 && kn < 20) ||
                      (row.range === '20-28 kn' && kn >= 20 && kn < 28) ||
                      (row.range === '> 28 kn' && kn >= 28)
                    return (
                      <View key={row.range} style={[s.windScaleRow, active && { backgroundColor: row.color + '15', borderRadius: 8 }]}>
                        <Ionicons name={row.icon} size={14} color={row.color} />
                        <Text style={[s.windScaleRange, active && { fontWeight: '800' }]}>{row.range}</Text>
                        <Text style={[s.windScaleLabel, { color: row.color }, active && { fontWeight: '800' }]}>{row.label}</Text>
                        {active && <Text style={[s.windScaleNow, { color: row.color }]}>{t('dash.now')}</Text>}
                      </View>
                    )
                  })}
                </View>
              </View>
            )}

            {/* TideWidget moved inside admin weather card (mobile) */}

            <View style={{ height: 40 }} />
          </>
        ) : null}
      </ScrollView>
    </View>
  )
}

// ─── Styles ────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: {
    paddingTop: Platform.OS === 'web' ? 20 : 56,
    paddingBottom: 20, paddingHorizontal: 24,
    flexDirection: 'row', alignItems: 'center', gap: 14,
    backgroundColor: C.surface,
    borderBottomWidth: 1, borderBottomColor: C.border,
  },
  headerLogo: {
    width: 52, height: 52, borderRadius: 14,
  },
  headerRight: { flexDirection: 'row', gap: 8 },
  headerBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: C.surfaceHigh, paddingHorizontal: 14, paddingVertical: 8,
    borderRadius: 12, borderWidth: 1, borderColor: C.border,
  },
  headerBadgeText: { color: C.textSec, fontSize: 13, fontWeight: '700' },
  date: { color: C.primary, fontSize: 12, fontWeight: '700', marginBottom: 2 },
  title: { color: C.text, fontSize: 24, fontWeight: '900', letterSpacing: -0.5 },

  scroll: { flex: 1 },
  scrollContent: { padding: 20 },
  loadingBox: { paddingTop: 60, alignItems: 'center' },

  // KPI summary bar
  kpiBar: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around',
    backgroundColor: C.surfaceHigh, borderRadius: 16, paddingVertical: 14, paddingHorizontal: 10,
    marginBottom: 16, borderWidth: 1, borderColor: C.primary + '30',
    shadowColor: C.primary, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 12, elevation: 8,
  },
  kpiItem: { alignItems: 'center', flex: 1 },
  kpiLabel: { color: C.textMuted, fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 3 },
  kpiValue: { color: C.text, fontSize: 15, fontWeight: '900' },
  kpiDivider: { width: 1, height: 30, backgroundColor: C.border },

  // Dashboard top row (weather left + stats right)
  dashTopRow: { flexDirection: 'row', gap: 12, marginBottom: 16 },

  // Stats column (right side)
  statsCol: { width: 170, gap: 10 },
  statCard: {
    flex: 1, backgroundColor: C.surface, borderRadius: 18, padding: 14,
    alignItems: 'center', borderWidth: 1, borderColor: C.border,
  },
  statIconBg: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center', marginBottom: 8 },
  statIcon: { fontSize: 18 },
  statValue: { fontSize: 26, fontWeight: '900', marginBottom: 2, letterSpacing: -1 },
  statLabel: { color: C.textMuted, fontSize: 11, fontWeight: '600', textAlign: 'center' },

  // Finance
  financeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 24 },
  finCard: {
    width: '47%' as any, backgroundColor: C.surface, borderRadius: 18, padding: 18,
    borderWidth: 1, borderColor: C.border, overflow: 'hidden' as any,
  },
  finCardEmoji: { fontSize: 28, marginBottom: 6 },
  finLabel: { color: C.textMuted, fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 },
  finValue: { fontSize: 22, fontWeight: '900', letterSpacing: -0.5 },
  finSub: { color: '#94a3b8', fontSize: 11, marginTop: 4 },

  // Team
  teamRow: { flexDirection: 'row', gap: 12, marginBottom: 24 },
  teamCard: {
    flex: 1, backgroundColor: C.surface, borderRadius: 18, padding: 18,
    alignItems: 'center', borderWidth: 1, borderColor: C.border,
  },
  teamIconBg: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center', marginBottom: 8 },
  teamValue: { color: C.text, fontSize: 28, fontWeight: '900', letterSpacing: -1 },
  teamLabel: { color: C.textMuted, fontSize: 12, fontWeight: '700' },

  // Quick actions
  sectionTitle: { color: C.text, fontSize: 18, fontWeight: '900', marginBottom: 14, letterSpacing: -0.3 },
  sectionRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  seeAll: { color: C.primary, fontSize: 13, fontWeight: '700', marginBottom: 14 },
  actionsRow: { flexDirection: 'row', gap: 10, marginBottom: 24 },
  action: { flex: 1, alignItems: 'center', gap: 8 },
  actionIcon: {
    width: 56, height: 56, borderRadius: 18, alignItems: 'center', justifyContent: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.1, shadowRadius: 8, elevation: 4,
  },
  actionEmoji: { fontSize: 24 },
  actionLabel: { color: '#475569', fontSize: 11, fontWeight: '700', textAlign: 'center' },

  // Today's lessons
  lessonCard: {
    backgroundColor: C.surface, borderRadius: 16, marginBottom: 10,
    flexDirection: 'row', alignItems: 'center', overflow: 'hidden',
    borderWidth: 1, borderColor: C.border,
  },
  lessonBar: { width: 4, minHeight: 72, borderTopLeftRadius: 16, borderBottomLeftRadius: 16 },
  lessonTime: { width: 54, alignItems: 'center', paddingHorizontal: 4 },
  lessonTimeText: { color: C.text, fontSize: 14, fontWeight: '900' },
  lessonTimeEnd: { color: C.textMuted, fontSize: 12, marginTop: 2, fontWeight: '600' },
  lessonInfo: { flex: 1, paddingVertical: 12, paddingHorizontal: 10 },
  lessonCustomer: { color: C.text, fontSize: 14, fontWeight: '800', marginBottom: 3 },
  lessonService: { color: C.textSec, fontSize: 12, fontWeight: '500', marginBottom: 4 },
  lessonMeta: { flexDirection: 'row', gap: 12, alignItems: 'center' },
  lessonMetaItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  lessonMetaText: { color: C.textMuted, fontSize: 11, fontWeight: '600' },
  lessonPayment: { fontSize: 11, fontWeight: '800' },
  lessonPrice: { color: C.text, fontSize: 14, fontWeight: '800', paddingRight: 14 },

  // Pending
  pendingCard: {
    backgroundColor: C.surface, borderRadius: 14, marginBottom: 10,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 14, borderWidth: 1, borderColor: C.warning + '40', borderLeftWidth: 4, borderLeftColor: C.warning,
  },
  pendingLeft: { flex: 1 },
  pendingName: { color: C.text, fontSize: 14, fontWeight: '700', marginBottom: 2 },
  pendingService: { color: C.textSec, fontSize: 11, marginBottom: 2 },
  pendingDate: { color: C.textMuted, fontSize: 12 },
  pendingRight: { alignItems: 'flex-end' },
  pendingPrice: { color: C.text, fontSize: 14, fontWeight: '700', marginBottom: 4 },
  pendingBadge: { backgroundColor: C.warning + '22', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  pendingBadgeText: { color: C.warning, fontSize: 12, fontWeight: '700' },
  badgeWarn: { backgroundColor: C.warning + '22', paddingHorizontal: 10, paddingVertical: 3, borderRadius: 10, marginBottom: 12, borderWidth: 1, borderColor: C.warning + '55' },
  badgeWarnText: { color: C.warning, fontSize: 12, fontWeight: '700' },

  // Empty
  emptyCard: {
    backgroundColor: C.surface, borderRadius: 20, padding: 28,
    alignItems: 'center', borderWidth: 1, borderColor: C.border, marginBottom: 24,
  },
  emptyIcon: { fontSize: 40, marginBottom: 12 },
  emptyTitle: { color: C.textSec, fontSize: 16, fontWeight: '700', marginBottom: 14 },
  emptyBtn: { backgroundColor: C.primary, paddingHorizontal: 22, paddingVertical: 11, borderRadius: 14 },
  emptyBtnText: { color: '#fff', fontSize: 14, fontWeight: '800' },

  // MEWIA alert (admin dashboard)
  mewiaAlert: {
    backgroundColor: C.warningSoft, borderRadius: 20, padding: 18,
    borderWidth: 1, borderColor: C.warning + '40', marginBottom: 16,
  },
  mewiaAlertTop: {
    flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 10,
  },
  mewiaAlertIconBox: {
    width: 44, height: 44, borderRadius: 14, backgroundColor: '#fbbf24',
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#f59e0b', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.3, shadowRadius: 8,
  },
  mewiaAlertContent: { flex: 1 },
  mewiaAlertTitle: {
    color: C.warning, fontSize: 18, fontWeight: '900', letterSpacing: 0.5,
  },
  mewiaAlertWind: {
    color: C.warning, fontSize: 12, fontWeight: '600', marginTop: 2,
  },
  mewiaAlertStats: {
    flexDirection: 'row', gap: 16, marginBottom: 8,
    backgroundColor: '#fff', borderRadius: 10, padding: 10,
  },
  mewiaAlertStat: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  mewiaAlertStatText: { color: C.warning, fontSize: 12, fontWeight: '700' },
  mewiaAlertNote: {
    color: C.warning, fontSize: 11, fontWeight: '500', fontStyle: 'italic',
  },

  // Rose + announcements row
  roseAnnouncementsRow: {
    flexDirection: 'row', gap: 14, marginTop: 12, alignItems: 'flex-start',
  },
  announcementsBox: { flex: 1 },
  announcementTitle: {
    color: C.textSec, fontSize: 11, fontWeight: '700', textTransform: 'uppercase',
    letterSpacing: 0.5, marginBottom: 8,
  },
  announcementItem: {
    flexDirection: 'row', gap: 8, marginBottom: 8, alignItems: 'flex-start',
  },
  announcementContent: { flex: 1 },
  announcementText: { color: C.text, fontSize: 12, fontWeight: '600', lineHeight: 16 },
  announcementMeta: { color: C.textMuted, fontSize: 12, marginTop: 2 },

  // Wind scale (dashboard)
  windScaleSection: {
    borderTopWidth: 1, borderTopColor: C.border, marginTop: 14, paddingTop: 10,
  },
  windScaleTitle: {
    color: C.textSec, fontSize: 11, fontWeight: '700', textTransform: 'uppercase',
    letterSpacing: 0.5, marginBottom: 6,
  },
  windScaleRow: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    paddingVertical: 4, paddingHorizontal: 6,
  },
  windScaleRange: { color: C.textSec, fontSize: 11, fontWeight: '600', width: 58 },
  windScaleLabel: { fontSize: 11, fontWeight: '600', flex: 1 },
  windScaleNow: { fontSize: 11, fontWeight: '900', letterSpacing: 0.5 },

  // ── Admin weather + WindRose card ──
  cardDecor: {
    position: 'absolute' as any, right: -10, top: -10,
    fontSize: 80, opacity: 0.12,
  },
  weatherIconCircle: {
    width: 56, height: 56, borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.8)',
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#0284c7', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.1, shadowRadius: 8,
  },
  adminWeatherCard: {
    flex: 1, backgroundColor: C.surface, borderRadius: 22, padding: 22,
    borderWidth: 1, borderColor: C.border, overflow: 'hidden' as any,
  },
  adminWeatherTopRow: {
    flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 16,
  },
  adminWeatherInfo: { },
  adminWeatherTemp: { color: C.text, fontSize: 36, fontWeight: '900', letterSpacing: -1 },
  adminWeatherLabel: { color: C.textSec, fontSize: 13, fontWeight: '600' },
  adminWeatherWindBadge: {
    alignItems: 'center', backgroundColor: C.primarySoft,
    paddingHorizontal: 14, paddingVertical: 10, borderRadius: 14, borderWidth: 1, borderColor: C.primary + '30',
  },
  adminWeatherWindValue: { color: C.primary, fontSize: 18, fontWeight: '900' },
  adminWeatherWindDir: { color: C.primary, fontSize: 12, fontWeight: '700' },
})

// ─── Instructor Dashboard Styles ──────────────────────────────────────

const ir = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: {
    backgroundColor: C.surface,
    paddingTop: Platform.OS === 'web' ? 24 : 56,
    paddingBottom: 16, paddingHorizontal: 20,
    borderBottomWidth: 1, borderBottomColor: C.border,
    flexDirection: 'row' as const, alignItems: 'center' as const, gap: 14,
  },
  headerLogo: { width: 44, height: 44 },
  date: { color: C.textMuted, fontSize: 12, fontWeight: '500', marginBottom: 2 },
  greeting: { color: C.text, fontSize: 22, fontWeight: '800', letterSpacing: -0.5 },

  scroll: { flex: 1 },
  scrollContent: { padding: 20 },
  loadingBox: { paddingTop: 60, alignItems: 'center' as const },

  // Empty / error states
  emptyCard: {
    backgroundColor: C.surface, borderRadius: 20, padding: 28,
    alignItems: 'center' as const, borderWidth: 1, borderColor: C.border, marginBottom: 20,
  },
  emptyIcon: { fontSize: 36, marginBottom: 10 },
  emptyTitle: { color: C.text, fontSize: 16, fontWeight: '700', marginBottom: 8, textAlign: 'center' as const },
  emptySubtitle: { color: C.textMuted, fontSize: 13, textAlign: 'center' as const },

  // Sections
  sectionRow: {
    flexDirection: 'row' as const, justifyContent: 'space-between' as const,
    alignItems: 'center' as const, marginBottom: 12, marginTop: 8,
  },
  sectionTitle: { color: C.text, fontSize: 16, fontWeight: '700' },
  sectionCount: {
    color: C.primary, fontSize: 14, fontWeight: '800',
    backgroundColor: C.primarySoft, paddingHorizontal: 10, paddingVertical: 3, borderRadius: 10,
  },
  seeAllLink: { color: C.primary, fontSize: 13, fontWeight: '600' },

  // ── Weather card ──
  weatherCard: {
    backgroundColor: C.surface, borderRadius: 20, padding: 20,
    borderWidth: 1, borderColor: C.border, marginBottom: 20,
  },
  weatherTopRow: {
    flexDirection: 'row' as const, alignItems: 'center' as const, gap: 14, marginBottom: 16,
  },
  weatherInfo: { flex: 1 },
  weatherTemp: { color: C.text, fontSize: 32, fontWeight: '800' },
  weatherLabel: { color: C.textSec, fontSize: 13, fontWeight: '600' },
  weatherWindBadge: {
    alignItems: 'center' as const, backgroundColor: C.primarySoft,
    paddingHorizontal: 12, paddingVertical: 8, borderRadius: 12,
  },
  weatherWindValue: { color: C.primary, fontSize: 16, fontWeight: '800' },
  weatherWindDir: { color: C.primary, fontSize: 11, fontWeight: '600' },

  // ── Lesson cards (today) ──
  lessonCard: {
    backgroundColor: C.surface, borderRadius: 16, marginBottom: 10,
    flexDirection: 'row' as const, alignItems: 'center' as const,
    padding: 14, borderWidth: 1, borderColor: C.border,
  },
  lessonTimeCol: { width: 52, alignItems: 'center' as const },
  lessonTimeText: { color: C.text, fontSize: 15, fontWeight: '800' },
  lessonTimeEnd: { color: C.textMuted, fontSize: 12, marginTop: 2 },
  lessonDivider: {
    width: 1, height: 46, backgroundColor: C.border, marginHorizontal: 10,
  },
  lessonInfo: { flex: 1 },
  lessonCustomerName: { color: C.text, fontSize: 15, fontWeight: '700', marginBottom: 2 },
  lessonService: { color: C.textSec, fontSize: 12, marginBottom: 4 },
  lessonMetaRow: { flexDirection: 'row' as const, gap: 8, alignItems: 'center' as const },
  lessonMeta: { color: C.textMuted, fontSize: 11, fontWeight: '500' },
  lessonPhone: { color: C.textMuted, fontSize: 11, marginTop: 4 },
  skillBadge: {
    paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8,
  },
  skillBadgeText: { fontSize: 12, fontWeight: '700', textTransform: 'capitalize' as const },
  statusDot: { width: 10, height: 10, borderRadius: 5, marginLeft: 8 },

  // ── Upcoming cards ──
  upcomingCard: {
    backgroundColor: C.surface, borderRadius: 14, marginBottom: 8,
    flexDirection: 'row' as const, alignItems: 'center' as const,
    padding: 12, borderWidth: 1, borderColor: C.border,
  },
  upcomingDateCol: { width: 48, alignItems: 'center' as const },
  upcomingDay: { color: C.primary, fontSize: 11, fontWeight: '600' },
  upcomingDate: { color: C.text, fontSize: 12, fontWeight: '700' },
  upcomingDivider: { width: 1, height: 32, backgroundColor: C.border, marginHorizontal: 10 },
  upcomingInfo: { flex: 1 },
  upcomingCustomer: { color: C.text, fontSize: 13, fontWeight: '600' },
  upcomingService: { color: C.textSec, fontSize: 11 },
  upcomingTime: { color: C.textSec, fontSize: 12, fontWeight: '600' },

  // ── MEWIA transfer card (instructor) ──
  mewiaBadge: {
    backgroundColor: C.warningSoft, paddingHorizontal: 10, paddingVertical: 3,
    borderRadius: 10, borderWidth: 1, borderColor: C.warning + '55',
  },
  mewiaBadgeText: { color: C.warning, fontSize: 12, fontWeight: '700' },
  mewiaCard: {
    backgroundColor: C.surface, borderRadius: 14, marginBottom: 10,
    flexDirection: 'row' as const, alignItems: 'flex-start' as const,
    padding: 14, borderWidth: 1, borderColor: C.warning + '40',
    borderLeftWidth: 3, borderLeftColor: C.warning,
    gap: 12,
  },
  mewiaCardInfo: { flex: 1 },
  mewiaCardCustomer: { color: C.text, fontSize: 14, fontWeight: '700', marginBottom: 2 },
  mewiaCardDetail: { color: C.textSec, fontSize: 12, marginBottom: 4 },
  mewiaStatusBadge: {
    alignSelf: 'flex-start' as const,
    paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8,
  },
  mewiaStatusText: { fontSize: 12, fontWeight: '700' },
  mewiaCardNotes: {
    color: C.textMuted, fontSize: 11, fontStyle: 'italic' as const, marginTop: 4,
  },
  mewiaCardTime: { color: C.textSec, fontSize: 12, fontWeight: '600' },
})
