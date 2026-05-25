import { isOwnerEmail } from '@/lib/owner'
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { useEffect } from 'react'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import { trackPageView } from '@/lib/analytics'
import { C } from '@/constants/Colors'

// ─── Owner guard ──────────────────────────────────────────────────────────


// ─── Data fetching ────────────────────────────────────────────────────────

interface TopItem { name: string; count: number }
interface UserItem { email: string; count: number }
interface DayItem { day: string; count: number }
interface ConfigItem { name: string; value: string; count: number }

interface UsageData {
  topPages: TopItem[]
  topFeatures: TopItem[]
  activeUsers: UserItem[]
  configs: ConfigItem[]
  dailyTrend: DayItem[]
  totalEvents: number
}

async function fetchUsageData(): Promise<UsageData> {
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()

  // Fetch all events from the last 7 days (max 5000)
  const { data: events, error } = await supabase
    .from('analytics_events')
    .select('event_type, event_name, event_data, user_email, created_at')
    .gte('created_at', sevenDaysAgo)
    .order('created_at', { ascending: false })
    .limit(5000)

  if (error) throw error
  const rows = events ?? []

  // Top pages
  const pageCounts = new Map<string, number>()
  const featureCounts = new Map<string, number>()
  const userCounts = new Map<string, number>()
  const configCounts = new Map<string, Map<string, number>>()
  const dayCounts = new Map<string, number>()

  for (const row of rows) {
    // User counts
    if (row.user_email) {
      userCounts.set(row.user_email, (userCounts.get(row.user_email) ?? 0) + 1)
    }

    // Daily trend
    const day = row.created_at?.slice(0, 10) ?? 'unknown'
    dayCounts.set(day, (dayCounts.get(day) ?? 0) + 1)

    if (row.event_type === 'page_view') {
      pageCounts.set(row.event_name, (pageCounts.get(row.event_name) ?? 0) + 1)
    } else if (row.event_type === 'feature_use') {
      featureCounts.set(row.event_name, (featureCounts.get(row.event_name) ?? 0) + 1)
    } else if (row.event_type === 'config_change') {
      const val = String(row.event_data?.value ?? '?')
      if (!configCounts.has(row.event_name)) configCounts.set(row.event_name, new Map())
      const inner = configCounts.get(row.event_name)!
      inner.set(val, (inner.get(val) ?? 0) + 1)
    }
  }

  const sort = (m: Map<string, number>): TopItem[] =>
    [...m.entries()].sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count }))

  const configs: ConfigItem[] = []
  for (const [name, valMap] of configCounts) {
    for (const [value, count] of valMap) {
      configs.push({ name, value, count })
    }
  }
  configs.sort((a, b) => b.count - a.count)

  const dailyTrend: DayItem[] = [...dayCounts.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([day, count]) => ({ day, count }))

  return {
    topPages: sort(pageCounts).slice(0, 15),
    topFeatures: sort(featureCounts).slice(0, 15),
    activeUsers: [...userCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([email, count]) => ({ email, count }))
      .slice(0, 15),
    configs,
    dailyTrend,
    totalEvents: rows.length,
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────

const PAGE_LABELS: Record<string, string> = {
  dashboard: 'Glowna',
  calendar: 'Kalendarz',
  bookings: 'Rezerwacje',
  booking_detail: 'Szczegoly rezerwacji',
  finances: 'Finanse',
  people: 'Ludzie',
  weather: 'Pogoda',
  settings: 'Ustawienia',
  mewia: 'MEWIA',
  services: 'Uslugi',
  equipment: 'Sprzet',
  analytics: 'Dane & CSV',
  usage: 'Uzycie panelu',
}

const FEATURE_LABELS: Record<string, string> = {
  view_mode_change: 'Zmiana widoku kalendarza',
  sport_filter: 'Filtr sportu',
  quick_add_booking: 'Szybkie dodanie rezerwacji',
  drag_booking: 'Przeciagniecie rezerwacji',
  resize_booking: 'Zmiana dlugosci lekcji',
  search_bookings: 'Wyszukiwanie rezerwacji',
  filter_status: 'Filtr statusu',
  confirm_booking: 'Potwierdzenie rezerwacji',
  complete_booking: 'Zakonczenie lekcji',
  mark_paid: 'Oznaczenie platnosci',
  mark_noshow: 'Nieobecnosc',
  delete_booking: 'Usuniecie rezerwacji',
  location_change: 'Zmiana lokalizacji',
  my_lessons_toggle: 'Filtr "Moje lekcje"',
}

// ─── Bar component ────────────────────────────────────────────────────────

function BarRow({ label, count, maxCount, color }: { label: string; count: number; maxCount: number; color: string }) {
  const pct = maxCount > 0 ? (count / maxCount) * 100 : 0
  return (
    <View style={s.barRow}>
      <View style={s.barLabelWrap}>
        <Text style={s.barLabel} numberOfLines={1}>{label}</Text>
        <Text style={s.barCount}>{count}</Text>
      </View>
      <View style={s.barTrack}>
        <View style={[s.barFill, { width: `${Math.max(2, pct)}%`, backgroundColor: color }]} />
      </View>
    </View>
  )
}

// ─── Screen ───────────────────────────────────────────────────────────────

export default function UsageScreen() {
  const router = useRouter()
  const { session, userRole } = useAuth()
  const userEmail = session?.user?.email?.toLowerCase() ?? ''

  useEffect(() => { trackPageView('usage') }, [])

  // Owner guard
  if (userRole !== 'admin' && !isOwnerEmail(userEmail, userRole)) {
    return (
      <View style={s.centered}>
        <Ionicons name="lock-closed-outline" size={48} color={C.textMuted} />
        <Text style={s.accessDenied}>Brak dostepu</Text>
        <Text style={s.accessDeniedSub}>Tylko wlasciciele maja dostep do analityki uzycia.</Text>
        <TouchableOpacity onPress={() => router.back()} style={s.backLinkBtn}>
          <Text style={s.backLinkText}>Wstecz</Text>
        </TouchableOpacity>
      </View>
    )
  }

  const { data, isLoading, isError } = useQuery({
    queryKey: ['usage_analytics'],
    queryFn: fetchUsageData,
    staleTime: 30000,
  })

  if (isLoading) {
    return (
      <View style={s.centered}>
        <ActivityIndicator size="large" color={C.primary} />
        <Text style={s.loadingText}>Ladowanie danych...</Text>
      </View>
    )
  }

  if (isError || !data) {
    return (
      <View style={s.centered}>
        <Ionicons name="alert-circle-outline" size={48} color={C.error} />
        <Text style={s.errorText}>Blad ladowania danych analityki.</Text>
        <Text style={s.errorSub}>Sprawdz czy tabela analytics_events istnieje w Supabase.</Text>
        <TouchableOpacity onPress={() => router.back()} style={s.backLinkBtn}>
          <Text style={s.backLinkText}>Wstecz</Text>
        </TouchableOpacity>
      </View>
    )
  }

  const maxPage = data.topPages[0]?.count ?? 1
  const maxFeature = data.topFeatures[0]?.count ?? 1
  const maxUser = data.activeUsers[0]?.count ?? 1
  const maxDay = Math.max(...data.dailyTrend.map(d => d.count), 1)

  return (
    <View style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} activeOpacity={0.7} style={s.backBtn}>
          <Ionicons name="chevron-back" size={20} color={C.textMuted} />
        </TouchableOpacity>
        <Text style={s.headerTitle}>Uzycie panelu</Text>
        <Text style={s.headerBadge}>{data.totalEvents} eventow (7 dni)</Text>
      </View>

      <ScrollView
        style={s.scroll}
        contentContainerStyle={{ paddingBottom: 60 }}
        showsVerticalScrollIndicator={true}
      >
        {/* ── Daily trend ── */}
        <View style={s.card}>
          <Text style={s.sectionTitle}>Aktywnosc dzienna</Text>
          {data.dailyTrend.length === 0 ? (
            <Text style={s.emptyText}>Brak danych</Text>
          ) : (
            data.dailyTrend.map(d => (
              <BarRow
                key={d.day}
                label={d.day.slice(5)}
                count={d.count}
                maxCount={maxDay}
                color="#0ea5e9"
              />
            ))
          )}
        </View>

        {/* ── Top pages ── */}
        <View style={s.card}>
          <Text style={s.sectionTitle}>Najczesciej odwiedzane ekrany</Text>
          {data.topPages.length === 0 ? (
            <Text style={s.emptyText}>Brak danych</Text>
          ) : (
            data.topPages.map(p => (
              <BarRow
                key={p.name}
                label={PAGE_LABELS[p.name] ?? p.name}
                count={p.count}
                maxCount={maxPage}
                color="#8b5cf6"
              />
            ))
          )}
        </View>

        {/* ── Top features ── */}
        <View style={s.card}>
          <Text style={s.sectionTitle}>Najczesciej uzywane funkcje</Text>
          {data.topFeatures.length === 0 ? (
            <Text style={s.emptyText}>Brak danych</Text>
          ) : (
            data.topFeatures.map(f => (
              <BarRow
                key={f.name}
                label={FEATURE_LABELS[f.name] ?? f.name}
                count={f.count}
                maxCount={maxFeature}
                color="#22c55e"
              />
            ))
          )}
        </View>

        {/* ── Active users ── */}
        <View style={s.card}>
          <Text style={s.sectionTitle}>Aktywni uzytkownicy</Text>
          {data.activeUsers.length === 0 ? (
            <Text style={s.emptyText}>Brak danych</Text>
          ) : (
            data.activeUsers.map(u => (
              <BarRow
                key={u.email}
                label={u.email.split('@')[0]}
                count={u.count}
                maxCount={maxUser}
                color="#f97316"
              />
            ))
          )}
        </View>

        {/* ── Config changes ── */}
        <View style={s.card}>
          <Text style={s.sectionTitle}>Konfiguracje</Text>
          {data.configs.length === 0 ? (
            <Text style={s.emptyText}>Brak zmian konfiguracji</Text>
          ) : (
            data.configs.map((c, i) => (
              <View key={`${c.name}-${c.value}-${i}`} style={s.configRow}>
                <Text style={s.configName}>{c.name}</Text>
                <View style={s.configBadge}>
                  <Text style={s.configValue}>{c.value}</Text>
                </View>
                <Text style={s.configCount}>{c.count}x</Text>
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </View>
  )
}

// ─── Styles ───────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },
  centered: { flex: 1, backgroundColor: C.bg, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
    backgroundColor: C.surface,
  },
  backBtn: {
    width: 32, height: 32, borderRadius: 8,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: C.bg,
  },
  headerTitle: { color: C.text, fontSize: 18, fontWeight: '800', flex: 1 },
  headerBadge: {
    color: C.textMuted, fontSize: 11, fontWeight: '600',
    backgroundColor: C.bg, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6,
  },

  scroll: { flex: 1, paddingHorizontal: 16, paddingTop: 16 },

  card: {
    backgroundColor: C.surface,
    borderRadius: 14,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: C.border,
  },
  sectionTitle: {
    color: C.text,
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 12,
  },

  // Bar chart rows
  barRow: { marginBottom: 8 },
  barLabelWrap: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 3,
  },
  barLabel: { color: C.text, fontSize: 12, fontWeight: '600', flex: 1 },
  barCount: { color: C.textMuted, fontSize: 12, fontWeight: '700', marginLeft: 8 },
  barTrack: {
    height: 8,
    backgroundColor: C.bg,
    borderRadius: 4,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 4,
  },

  // Config rows
  configRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  configName: { color: C.text, fontSize: 12, fontWeight: '600', flex: 1 },
  configBadge: {
    backgroundColor: C.primary + '18',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  configValue: { color: C.primary, fontSize: 11, fontWeight: '700' },
  configCount: { color: C.textMuted, fontSize: 12, fontWeight: '600', width: 30, textAlign: 'right' },

  // States
  loadingText: { color: C.textMuted, fontSize: 14, marginTop: 12 },
  emptyText: { color: C.textMuted, fontSize: 13, textAlign: 'center', paddingVertical: 16 },
  errorText: { color: C.error, fontSize: 14, fontWeight: '600', marginTop: 12 },
  errorSub: { color: C.textMuted, fontSize: 12, marginTop: 4, textAlign: 'center' },
  accessDenied: { color: C.text, fontSize: 18, fontWeight: '700', marginTop: 16 },
  accessDeniedSub: { color: C.textMuted, fontSize: 13, textAlign: 'center', marginTop: 6 },
  backLinkBtn: { marginTop: 20 },
  backLinkText: { color: C.primary, fontSize: 14, fontWeight: '600' },
})
