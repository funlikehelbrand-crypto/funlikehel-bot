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
import { Ionicons } from '@expo/vector-icons'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import type { BookingRow, BookingStatus, PaymentStatus } from '@/types'
import { C } from '@/constants/Colors'
import { trackPageView, trackFeature } from '@/lib/analytics'
import { ViewToggle, getViewMode, saveViewMode, type ViewMode } from '@/components/ViewToggle'
import { useLang } from '@/lib/i18n'

// ─── Constants ─────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  pending: '#f59e0b',
  confirmed: '#0ea5e9',
  in_progress: '#22c55e',
  completed: '#475569',
  cancelled: '#ef4444',
  no_show: '#ef4444',
  rescheduled: '#a855f7',
  weather_hold: '#64748b',
  deleted: '#94a3b8',
}

const PAYMENT_COLOR: Record<string, string> = {
  unpaid: '#ef4444',
  deposit_paid: '#f59e0b',
  paid: '#22c55e',
  refunded: '#475569',
  partial_refund: '#f59e0b',
}

type FilterStatus = BookingStatus | 'all' | 'deleted'

const STATUS_FILTER_KEYS: Array<{ value: FilterStatus; i18nKey: string }> = [
  { value: 'all', i18nKey: 'book.all' },
  { value: 'pending', i18nKey: 'book.pending' },
  { value: 'confirmed', i18nKey: 'book.confirmed' },
  { value: 'in_progress', i18nKey: 'book.active' },
  { value: 'completed', i18nKey: 'book.completed' },
  { value: 'cancelled', i18nKey: 'book.cancelled' },
  { value: 'deleted', i18nKey: 'book.archive' },
]

// ─── Data fetching ─────────────────────────────────────────────────────────

async function fetchBookings(
  location: string,
  statusFilter: FilterStatus,
  search: string,
  season: string = '2026',
  customerEmail?: string,
): Promise<(BookingRow & { cancel_reason?: string | null })[]> {
  let query = supabase
    .from('bookings')
    .select(`
      id, booking_ref, customer_name, customer_email,
      service_name_snap, location, start_date, start_time,
      instructor_snap, persons, booking_status, payment_status,
      total_price, currency, created_at, cancel_reason, admin_notes, source
    `)
    .order('start_date', { ascending: false })
    .limit(500)

  // Customer sees ONLY their own bookings — no season/location filter needed
  if (customerEmail) {
    query = query.eq('customer_email', customerEmail)
  } else {
    // Season filter: 2025 = legacy import, 2026 = new, all = everything
    if (season === '2025') {
      query = query.eq('external_channel', 'legacy_import')
    } else if (season === '2026') {
      query = query.or('external_channel.is.null,external_channel.neq.legacy_import')
    }
    // 'all' = no filter

    if (location !== 'both') {
      query = query.eq('location', location)
    }
  }

  if (statusFilter === 'deleted') {
    // Archiwum — cancelled z markerem [ARCHIVED]
    query = query.eq('booking_status', 'cancelled').like('cancel_reason', '[ARCHIVED]%')
  } else if (statusFilter !== 'all') {
    query = query.eq('booking_status', statusFilter)
  } else {
    // "Wszystko" — wyklucz zarchiwizowane
    query = query.not('cancel_reason', 'like', '[ARCHIVED]%')
  }

  if (search.trim()) {
    query = query.or(
      `customer_name.ilike.%${search}%,booking_ref.ilike.%${search}%,customer_email.ilike.%${search}%`,
    )
  }

  const { data, error } = await query
  if (error) throw error
  return (data ?? []) as (BookingRow & { cancel_reason?: string | null })[]
}

// ─── Bookings List Screen ──────────────────────────────────────────────────

export default function BookingsScreen() {
  const { selectedLocation, selectedSeason, userRole, session } = useAuth()
  const router = useRouter()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all')
  const [refreshing, setRefreshing] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>(() => getViewMode('bookings'))

  const isCustomer = userRole === 'customer'
  const customerEmail = isCustomer ? (session?.user?.email ?? undefined) : undefined
  const { t } = useLang()

  useEffect(() => { trackPageView('bookings') }, [])

  const { data: bookings, isLoading, isError, refetch } = useQuery({
    queryKey: ['bookings', selectedLocation, statusFilter, search, selectedSeason, customerEmail],
    queryFn: () => fetchBookings(selectedLocation, statusFilter, search, selectedSeason, customerEmail),
    staleTime: 15000,
  })

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    await refetch()
    setRefreshing(false)
  }, [refetch])

  return (
    <View style={s.root}>
      {/* Header */}
      <View style={s.header}>
        <View style={s.headerRow}>
          <Text style={s.title}>{isCustomer ? t('book.my_bookings') : t('book.title')}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <ViewToggle mode={viewMode} onChange={(m) => { setViewMode(m); saveViewMode('bookings', m) }} />
            {!isCustomer && (
              <TouchableOpacity
                onPress={() => router.push('/(app)/bookings/new')}
                style={s.newBtn}
                activeOpacity={0.8}
              >
                <Ionicons name="add" size={18} color={C.bg} />
                <Text style={s.newBtnText}>{t('book.new')}</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>

        {/* Search */}
        <View style={s.searchRow}>
          <Ionicons name="search-outline" size={16} color={C.textSec} style={s.searchIcon} />
          <TextInput
            style={s.searchInput}
            placeholder={t('book.search')}
            placeholderTextColor={C.textSec}
            value={search}
            onChangeText={(v) => { setSearch(v); if (v.length === 1) trackFeature('search_bookings', { query: true }) }}
            returnKeyType="search"
            autoCorrect={false}
          />
          {search.length > 0 && (
            <TouchableOpacity onPress={() => setSearch('')} hitSlop={8} activeOpacity={0.7}>
              <Ionicons name="close-circle" size={16} color={C.textSec} />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Status filter chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={s.chipsScroll}
        contentContainerStyle={s.chipsContent}
      >
        {STATUS_FILTER_KEYS.map((f) => {
          const isActive = statusFilter === f.value
          const color = f.value === 'all' ? C.primary : STATUS_COLOR[f.value] ?? C.primary
          return (
            <TouchableOpacity
              key={f.value}
              onPress={() => { setStatusFilter(f.value); trackFeature('filter_status', { status: f.value }) }}
              activeOpacity={0.75}
              style={[
                s.chip,
                {
                  backgroundColor: isActive ? `${color}22` : C.surface,
                  borderColor: isActive ? color : C.border,
                },
              ]}
            >
              <Text style={[s.chipText, { color: isActive ? color : C.textSec }]}>
                {t(f.i18nKey)}
              </Text>
            </TouchableOpacity>
          )
        })}
      </ScrollView>

      {/* List */}
      <ScrollView
        style={s.list}
        contentContainerStyle={s.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={C.primary}
            colors={[C.primary]}
          />
        }
        showsVerticalScrollIndicator={true}
      >
        {isLoading ? (
          <ActivityIndicator color={C.primary} style={s.loader} />
        ) : isError ? (
          <View style={s.errorBox}>
            <Text style={s.errorText}>Nie udało się załadować. Odśwież.</Text>
          </View>
        ) : !bookings?.length ? (
          <View style={s.empty}>
            <Ionicons name="clipboard-outline" size={48} color={C.border} />
            <Text style={s.emptyText}>{t('book.no_bookings')}</Text>
            {search ? (
              <TouchableOpacity onPress={() => setSearch('')} activeOpacity={0.7} style={s.clearBtn}>
                <Text style={s.clearBtnText}>Wyczyść</Text>
              </TouchableOpacity>
            ) : null}
          </View>
        ) : viewMode === 'grid' ? (
          <View style={s.gridWrap}>
            {bookings.map((booking) => {
              const statusColor = STATUS_COLOR[booking.booking_status] ?? C.textSec
              return (
                <TouchableOpacity
                  key={booking.id}
                  onPress={() => router.push(`/(app)/bookings/${booking.id}`)}
                  style={s.gridCard}
                  activeOpacity={0.8}
                >
                  <View style={[s.gridStatusDot, { backgroundColor: statusColor }]} />
                  <Text style={s.gridName} numberOfLines={1}>{booking.customer_name}</Text>
                  <Text style={s.gridService} numberOfLines={1}>{booking.service_name_snap}</Text>
                  <Text style={s.gridMeta}>
                    {format(new Date(booking.start_date), 'd MMM')}
                    {booking.start_time ? ` · ${(booking.start_time as string).slice(0, 5)}` : ''}
                  </Text>
                  {booking.total_price > 0 && (
                    <Text style={s.gridPrice}>{booking.total_price} {booking.currency}</Text>
                  )}
                </TouchableOpacity>
              )
            })}
          </View>
        ) : (
          bookings.map((booking) => {
            const statusColor = STATUS_COLOR[booking.booking_status] ?? C.textSec
            const payColor = PAYMENT_COLOR[booking.payment_status] ?? C.textSec

            return (
              <TouchableOpacity
                key={booking.id}
                onPress={() => router.push(`/(app)/bookings/${booking.id}`)}
                style={s.card}
                activeOpacity={0.8}
              >
                <View style={s.cardRow}>
                  <View style={[s.cardStatusBar, { backgroundColor: statusColor }]} />
                  <View style={s.cardBody}>
                    <View style={s.cardTopLine}>
                      <Text style={s.customerName} numberOfLines={1}>{booking.customer_name}</Text>
                      <View style={s.badgeRow}>
                        <View style={[s.badge, { backgroundColor: `${statusColor}18`, borderWidth: 1, borderColor: `${statusColor}40` }]}>
                          <Text style={[s.badgeText, { color: statusColor }]}>
                            {(booking.booking_status as string).replace('_', ' ')}
                          </Text>
                        </View>
                        <View style={[s.badge, { backgroundColor: `${payColor}18`, borderWidth: 1, borderColor: `${payColor}40` }]}>
                          <Text style={[s.badgeText, { color: payColor }]}>
                            {(booking.payment_status as string).replace('_', ' ')}
                          </Text>
                        </View>
                      </View>
                    </View>
                    <View style={s.cardBottomLine}>
                      <Text style={s.serviceName} numberOfLines={1}>{booking.service_name_snap}</Text>
                      <View style={s.metaRow}>
                        <Text style={s.metaText}>{format(new Date(booking.start_date), 'd MMM')}</Text>
                        {booking.start_time && <Text style={s.metaText}>{(booking.start_time as string).slice(0, 5)}</Text>}
                        <Text style={s.metaText}>{booking.persons} {t('book.persons')}</Text>
                        {booking.total_price > 0 && <Text style={s.price}>{booking.total_price} {booking.currency}</Text>}
                      </View>
                    </View>
                  </View>
                </View>
                {booking.booking_status === 'deleted' && booking.cancel_reason && (
                  <View style={s.deleteReasonRow}>
                    <Ionicons name="archive-outline" size={11} color={C.textMuted} />
                    <Text style={s.deleteReasonText} numberOfLines={1}>{booking.cancel_reason}</Text>
                  </View>
                )}
              </TouchableOpacity>
            )
          })
        )}
      </ScrollView>
    </View>
  )
}

// ─── Styles ────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: C.bg,
  },

  // Header
  header: {
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'web' ? 24 : 56,
    paddingBottom: 12,
    backgroundColor: C.bg,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: C.text,
  },
  newBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: C.primary,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 12,
  },
  newBtnText: {
    color: C.bg,
    fontSize: 14,
    fontWeight: '600',
  },

  // Search
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: C.surface,
    borderRadius: 12,
    paddingHorizontal: 16,
    height: 44,
    marginBottom: 4,
    borderWidth: 1,
    borderColor: C.border,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    color: C.text,
    fontSize: 14,
  },

  // Filter chips
  chipsScroll: {
    marginBottom: 12,
    maxHeight: 38,
    flexGrow: 0,
  },
  chipsContent: {
    paddingHorizontal: 20,
    gap: 8,
    alignItems: 'center' as any,
  },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 999,
    borderWidth: 1,
  },
  chipText: {
    fontSize: 12,
    fontWeight: '600',
  },

  // List
  list: {
    flex: 1,
    paddingHorizontal: 20,
  },
  listContent: {
    paddingBottom: 100,
  },
  loader: {
    marginTop: 40,
  },

  // Error
  errorBox: {
    backgroundColor: C.error + '20',
    borderWidth: 1,
    borderColor: C.error + '60',
    borderRadius: 16,
    padding: 16,
    marginTop: 16,
  },
  errorText: {
    color: C.error,
    fontSize: 14,
    textAlign: 'center',
  },

  // Empty state
  empty: {
    alignItems: 'center',
    marginTop: 64,
  },
  emptyText: {
    color: C.textSec,
    marginTop: 12,
    fontSize: 16,
  },
  clearBtn: {
    marginTop: 8,
  },
  clearBtnText: {
    color: C.primary,
    fontSize: 14,
  },

  // Booking card — compact row
  card: {
    backgroundColor: C.surface,
    borderRadius: 10,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: C.border,
    overflow: 'hidden' as any,
  },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'stretch',
  },
  cardStatusBar: {
    width: 4,
  },
  cardBody: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    gap: 2,
  },
  cardTopLine: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  cardBottomLine: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  badgeRow: {
    flexDirection: 'row',
    gap: 4,
  },
  badge: {
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 999,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  customerName: {
    color: C.text,
    fontSize: 13,
    fontWeight: '700',
    flex: 1,
    minWidth: 0,
  },
  serviceName: {
    color: C.textSec,
    fontSize: 12,
    flex: 1,
    minWidth: 0,
  },

  // Meta (date / time / persons / price) — inline
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  metaText: {
    color: C.textMuted,
    fontSize: 11,
  },
  price: {
    color: C.text,
    fontSize: 11,
    fontWeight: '700',
  },

  // Delete reason (archiwum)
  deleteReasonRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 12,
    paddingBottom: 6,
  },
  deleteReasonText: {
    color: C.textMuted,
    fontSize: 10,
    fontStyle: 'italic',
    flex: 1,
  },

  // Grid view
  gridWrap: {
    flexDirection: 'row', flexWrap: 'wrap', gap: 8,
  },
  gridCard: {
    flexBasis: '31%' as any, minWidth: 140, flexGrow: 1,
    backgroundColor: C.surface, borderRadius: 10, padding: 10,
    borderWidth: 1, borderColor: C.border,
  },
  gridStatusDot: {
    width: 8, height: 8, borderRadius: 4, marginBottom: 6,
  },
  gridName: {
    color: C.text, fontSize: 12, fontWeight: '700', marginBottom: 2,
  },
  gridService: {
    color: C.textMuted, fontSize: 10, marginBottom: 4,
  },
  gridMeta: {
    color: C.textSec, fontSize: 9,
  },
  gridPrice: {
    color: C.success, fontSize: 11, fontWeight: '800', marginTop: 4,
  },
})
