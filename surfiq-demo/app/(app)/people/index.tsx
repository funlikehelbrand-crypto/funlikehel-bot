import {
  ActivityIndicator,
  Platform,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import { useCallback, useState, useEffect } from 'react'
import { useRouter } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { Ionicons } from '@expo/vector-icons'
import { useAuth } from '@/contexts/AuthContext'
import type { CustomerRow, InstructorRow } from '@/types'
import { C } from '@/constants/Colors'
import { trackPageView } from '@/lib/analytics'
import { ViewToggle, getViewMode, saveViewMode, type ViewMode } from '@/components/ViewToggle'

// ─── Data fetching ─────────────────────────────────────────────────────────────

async function fetchCustomers(search: string): Promise<CustomerRow[]> {
  let query = supabase
    .from('customers')
    .select('id, first_name, last_name, email, phone, skill_level, total_lessons, total_paid, tags')
    .order('last_name', { ascending: true })
    .limit(500)

  if (search.trim()) {
    query = query.or(
      `first_name.ilike.%${search}%,last_name.ilike.%${search}%,email.ilike.%${search}%`,
    )
  }

  const { data, error } = await query
  if (error) throw error
  return (data ?? []) as CustomerRow[]
}

async function fetchInstructors(location: string): Promise<InstructorRow[]> {
  let query = supabase
    .from('instructors')
    .select('id, first_name, last_name, email, phone, location, is_active, color_hex, disciplines')
    .eq('is_active', true)
    .order('first_name', { ascending: true })

  if (location !== 'both') {
    query = query.or(`location.eq.${location},location.eq.both`)
  }

  const { data, error } = await query
  if (error) throw error
  return (data ?? []) as InstructorRow[]
}

// ─── Skill badge colors ────────────────────────────────────────────────────────

const SKILL_COLORS: Record<string, string> = {
  beginner: '#22c55e',
  basic: '#0ea5e9',
  intermediate: '#f59e0b',
  advanced: '#a855f7',
  professional: '#ef4444',
}

// ─── Screen ─────────────────────────────────────────────────────────────────────

export default function PeopleScreen() {
  const { selectedLocation } = useAuth()
  const router = useRouter()
  const [tab, setTab] = useState<'customers' | 'instructors'>('customers')
  const [search, setSearch] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>(() => getViewMode('people'))
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => { trackPageView('people') }, [])

  const { data: customers, isLoading: customersLoading, refetch: refetchCustomers } = useQuery({
    queryKey: ['customers', search],
    queryFn: () => fetchCustomers(search),
    enabled: tab === 'customers',
  })

  const { data: instructors, isLoading: instructorsLoading, refetch: refetchInstructors } = useQuery({
    queryKey: ['instructors', selectedLocation],
    queryFn: () => fetchInstructors(selectedLocation),
    enabled: tab === 'instructors',
  })

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    if (tab === 'customers') await refetchCustomers()
    else await refetchInstructors()
    setRefreshing(false)
  }, [tab, refetchCustomers, refetchInstructors])

  const isLoading = tab === 'customers' ? customersLoading : instructorsLoading

  const handleAdd = () => {
    if (tab === 'customers') router.push('/(app)/people/customer/new' as any)
    else router.push('/(app)/people/instructor/new' as any)
  }

  return (
    <View style={s.root}>
      {/* Header */}
      <View style={s.header}>
        <View style={s.titleRow}>
          <Text style={s.title}>Klienci</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <ViewToggle mode={viewMode} onChange={(m) => { setViewMode(m); saveViewMode('people', m) }} />
            <TouchableOpacity style={s.addBtn} onPress={handleAdd} activeOpacity={0.8}>
              <Text style={s.addBtnText}>+ Dodaj</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Tab switcher */}
        <View style={s.tabRow}>
          {(['customers', 'instructors'] as const).map((t) => (
            <TouchableOpacity
              key={t}
              onPress={() => setTab(t)}
              style={[s.tabBtn, tab === t && s.tabBtnActive]}
              activeOpacity={0.7}
            >
              <View style={s.tabContent}>
                <Ionicons
                  name={t === 'customers' ? 'people-outline' : 'fitness-outline'}
                  size={16}
                  color={tab === t ? '#fff' : C.textMuted}
                />
                <Text style={[s.tabText, tab === t && s.tabTextActive]}>
                  {t === 'customers' ? 'Klienci' : 'Instruktorzy'}
                </Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* Search — customers only */}
        {tab === 'customers' && (
          <View style={s.searchRow}>
            <Ionicons name="search-outline" size={16} color={C.textMuted} style={{ marginRight: 8 }} />
            <TextInput
              style={s.searchInput}
              placeholder="Szukaj klientów..."
              placeholderTextColor={C.textMuted}
              value={search}
              onChangeText={setSearch}
              returnKeyType="search"
              autoCorrect={false}
            />
            {search.length > 0 && (
              <TouchableOpacity onPress={() => setSearch('')} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                <Ionicons name="close-circle" size={18} color={C.textMuted} />
              </TouchableOpacity>
            )}
          </View>
        )}
      </View>

      {/* ── Customers ───────────────────────────────────────────────────── */}
      {tab === 'customers' && (
        <ScrollView
          style={s.scroll}
          contentContainerStyle={s.scrollContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={C.primary} colors={[C.primary]} />
          }
          showsVerticalScrollIndicator={true}
        >
          {isLoading ? (
            <ActivityIndicator color={C.primary} style={{ marginTop: 48 }} />
          ) : !customers?.length ? (
            <View style={s.emptyBox}>
              <Ionicons name="person-outline" size={48} color={C.textMuted} />
              <Text style={s.emptyTitle}>{search ? 'Brak wyników' : 'Brak klientów'}</Text>
              <Text style={s.emptySubtitle}>{search ? 'Spróbuj innej frazy' : 'Dodaj pierwszego klienta'}</Text>
              {!search && (
                <TouchableOpacity style={s.emptyBtn} onPress={handleAdd} activeOpacity={0.8}>
                  <Text style={s.emptyBtnText}>+ Dodaj klienta</Text>
                </TouchableOpacity>
              )}
            </View>
          ) : viewMode === 'grid' ? (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {customers.map((c) => {
                const skillColor = SKILL_COLORS[c.skill_level ?? ''] ?? C.textMuted
                const initials = `${c.first_name?.[0] ?? ''}${c.last_name?.[0] ?? ''}`
                return (
                  <TouchableOpacity
                    key={c.id}
                    onPress={() => router.push(`/(app)/people/customer/${c.id}` as any)}
                    style={{ flexBasis: '31%' as any, minWidth: 130, flexGrow: 1, backgroundColor: C.surface, borderRadius: 10, padding: 10, borderWidth: 1, borderColor: C.border, alignItems: 'center' }}
                    activeOpacity={0.75}
                  >
                    <View style={[s.avatar, { marginBottom: 6 }]}>
                      <Text style={s.avatarText}>{initials}</Text>
                    </View>
                    <Text style={{ color: C.text, fontSize: 12, fontWeight: '700', textAlign: 'center' }} numberOfLines={1}>{c.first_name} {c.last_name}</Text>
                    {c.skill_level && (
                      <View style={[s.skillPill, { backgroundColor: skillColor + '20', marginTop: 4 }]}>
                        <Text style={[s.skillText, { color: skillColor }]}>{c.skill_level}</Text>
                      </View>
                    )}
                    <Text style={{ color: C.textMuted, fontSize: 9, marginTop: 2 }}>{c.total_lessons} lekcji</Text>
                  </TouchableOpacity>
                )
              })}
            </View>
          ) : (
            customers.map((c) => {
              const skillColor = SKILL_COLORS[c.skill_level ?? ''] ?? C.textMuted
              const initials = `${c.first_name?.[0] ?? ''}${c.last_name?.[0] ?? ''}`
              return (
                <TouchableOpacity
                  key={c.id}
                  onPress={() => router.push(`/(app)/people/customer/${c.id}` as any)}
                  style={s.card}
                  activeOpacity={0.75}
                >
                  <View style={s.avatar}>
                    <Text style={s.avatarText}>{initials}</Text>
                  </View>
                  <View style={s.cardContent}>
                    <Text style={s.cardName}>{c.first_name} {c.last_name}</Text>
                    <Text style={s.cardEmail}>{c.email}</Text>
                    <View style={s.cardMeta}>
                      {c.skill_level && (
                        <View style={[s.skillPill, { backgroundColor: skillColor + '20' }]}>
                          <Text style={[s.skillText, { color: skillColor }]}>{c.skill_level}</Text>
                        </View>
                      )}
                      <Text style={s.lessonsText}>{c.total_lessons} lekcji</Text>
                    </View>
                  </View>
                  <Ionicons name="chevron-forward" size={18} color={C.border} />
                </TouchableOpacity>
              )
            })
          )}
        </ScrollView>
      )}

      {/* ── Instructors ─────────────────────────────────────────────────── */}
      {tab === 'instructors' && (
        <ScrollView
          style={s.scroll}
          contentContainerStyle={s.scrollContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={C.primary} colors={[C.primary]} />
          }
          showsVerticalScrollIndicator={true}
        >
          {isLoading ? (
            <ActivityIndicator color={C.primary} style={{ marginTop: 48 }} />
          ) : !instructors?.length ? (
            <View style={s.emptyBox}>
              <Ionicons name="fitness-outline" size={48} color={C.textMuted} />
              <Text style={s.emptyTitle}>Brak instruktorów</Text>
              <Text style={s.emptySubtitle}>Dodaj pierwszego instruktora</Text>
              <TouchableOpacity style={s.emptyBtn} onPress={handleAdd} activeOpacity={0.8}>
                <Text style={s.emptyBtnText}>+ Dodaj instruktora</Text>
              </TouchableOpacity>
            </View>
          ) : (
            instructors.map((inst) => {
              const initials = `${inst.first_name?.[0] ?? ''}${inst.last_name?.[0] ?? ''}`
              return (
                <TouchableOpacity
                  key={inst.id}
                  onPress={() => router.push(`/(app)/people/instructor/${inst.id}` as any)}
                  style={s.card}
                  activeOpacity={0.75}
                >
                  {/* Color avatar */}
                  <View style={[s.avatar, { backgroundColor: inst.color_hex ?? C.primary }]}>
                    <Text style={s.avatarText}>{initials}</Text>
                  </View>

                  <View style={s.cardContent}>
                    <Text style={s.cardName}>{inst.first_name} {inst.last_name}</Text>
                    <View style={s.locRow}>
                      <Ionicons name="location-outline" size={13} color={C.textSec} />
                      <Text style={s.cardEmail}>
                        {inst.location === 'hel' ? 'Hel' : inst.location === 'hurghada' ? 'Hurghada' : 'Oba'}
                      </Text>
                    </View>
                    {inst.disciplines && inst.disciplines.length > 0 && (
                      <Text style={s.lessonsText}>{inst.disciplines.join(' · ')}</Text>
                    )}
                  </View>

                  <View style={s.activeDot} />
                  <Ionicons name="chevron-forward" size={18} color={C.border} />
                </TouchableOpacity>
              )
            })
          )}
        </ScrollView>
      )}

      {/* FAB */}
      <View style={s.fab}>
        <TouchableOpacity style={s.fabBtn} onPress={handleAdd} activeOpacity={0.85}>
          <Ionicons name="add" size={28} color="#fff" />
        </TouchableOpacity>
      </View>
    </View>
  )
}

// ─── Styles ────────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },

  header: {
    backgroundColor: C.surface,
    paddingTop: Platform.OS === 'web' ? 24 : 56,
    paddingHorizontal: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  title: { color: C.text, fontSize: 22, fontWeight: '800', letterSpacing: -0.5 },
  addBtn: {
    backgroundColor: C.primary + '22', borderWidth: 1, borderColor: C.primary,
    paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20,
  },
  addBtnText: { color: C.primary, fontSize: 13, fontWeight: '700' },

  tabRow: {
    flexDirection: 'row', backgroundColor: C.surfaceHigh, borderRadius: 14,
    padding: 4, marginBottom: 14, borderWidth: 1, borderColor: C.border,
  },
  tabBtn: { flex: 1, paddingVertical: 10, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  tabContent: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  tabBtnActive: { backgroundColor: C.primary, borderColor: C.primary },
  tabText: { color: C.textMuted, fontSize: 13, fontWeight: '600' },
  tabTextActive: { color: '#fff' },

  searchRow: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: C.surfaceHigh,
    borderRadius: 12, paddingHorizontal: 14, height: 44,
    borderWidth: 1, borderColor: C.border,
  },
  searchIcon: { fontSize: 14, marginRight: 8 },
  searchInput: { flex: 1, color: C.text, fontSize: 14 },
  clearIcon: { color: C.textMuted, fontSize: 14, fontWeight: '700' },

  scroll: { flex: 1 },
  scrollContent: { padding: 20, paddingBottom: 120 },

  emptyBox: { alignItems: 'center', paddingTop: 60 },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { color: C.text, fontSize: 16, fontWeight: '700', marginBottom: 6 },
  emptySubtitle: { color: C.textMuted, fontSize: 13, marginBottom: 20 },
  emptyBtn: { backgroundColor: C.primary, paddingHorizontal: 22, paddingVertical: 10, borderRadius: 12 },
  emptyBtnText: { color: '#fff', fontSize: 13, fontWeight: '700' },

  card: {
    backgroundColor: C.surface, borderRadius: 16, padding: 14, marginBottom: 10,
    flexDirection: 'row', alignItems: 'center',
    borderWidth: 1, borderColor: C.border,
  },
  avatar: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: C.surfaceHigh, alignItems: 'center', justifyContent: 'center',
    marginRight: 14, flexShrink: 0,
  },
  avatarText: { color: C.text, fontSize: 15, fontWeight: '700' },
  cardContent: { flex: 1 },
  cardName: { color: C.text, fontSize: 15, fontWeight: '700', marginBottom: 2 },
  cardEmail: { color: C.textSec, fontSize: 12, marginBottom: 4 },
  cardMeta: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  skillPill: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  skillText: { fontSize: 10, fontWeight: '700', textTransform: 'capitalize' },
  lessonsText: { color: C.textMuted, fontSize: 11 },
  locRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 4 },
  activeDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: C.success, marginRight: 10 },

  fab: { position: 'absolute', bottom: 28, right: 20 },
  fabBtn: {
    width: 56, height: 56, borderRadius: 28, backgroundColor: C.primary,
    alignItems: 'center', justifyContent: 'center',
    shadowColor: C.primary, shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4, shadowRadius: 8, elevation: 8,
  },
  fabIcon: { color: '#fff', fontSize: 28, fontWeight: '300', lineHeight: 32 },
})
