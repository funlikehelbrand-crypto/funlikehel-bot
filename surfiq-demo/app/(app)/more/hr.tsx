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
import { useState, useMemo, useCallback } from 'react'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useQuery } from '@tanstack/react-query'
import {
  format,
  startOfMonth,
  endOfMonth,
  subMonths,
} from 'date-fns'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import { C } from '@/constants/Colors'
import { ViewToggle, getViewMode, saveViewMode, type ViewMode } from '@/components/ViewToggle'
import type { InstructorRow } from '@/types'

// ─── Owner-only guard ─────────────────────────────────────────────────────


// ─── Types ────────────────────────────────────────────────────────────────

type PeriodKey = 'this_month' | 'last_month' | 'custom'
type TabKey = 'salary' | 'expenses'

interface RawBooking {
  id: string
  instructor_id: string | null
  instructor_snap: string | null
  duration_hours: number | null
  start_time: string | null
  end_time: string | null
  start_date: string
  persons: number
  total_price: number
  currency: string
  booking_status: string
}

interface InstructorSalary {
  id: string
  name: string
  hours: number
  lessons: number
  rate: number | null
  salary: number
  bonus: number
  bonusNote: string
  total: number
  revenuePLN: number
  revenueEUR: number
}

interface Expense {
  id: string
  date: string
  amount: number
  category: string
  description: string
  created_by: string
}

const EXPENSE_CATEGORIES = ['sprzet', 'paliwo', 'jedzenie', 'transport', 'inne'] as const
const EXPENSE_LABELS: Record<string, string> = {
  sprzet: 'Sprzet',
  paliwo: 'Paliwo',
  jedzenie: 'Jedzenie',
  transport: 'Transport',
  inne: 'Inne',
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

// ─── Period helpers ───────────────────────────────────────────────────────

function getPeriodRange(
  key: PeriodKey,
  customFrom?: string,
  customTo?: string,
): { from: string; to: string; label: string } {
  const now = new Date()
  switch (key) {
    case 'this_month':
      return {
        from: format(startOfMonth(now), 'yyyy-MM-dd'),
        to: format(endOfMonth(now), 'yyyy-MM-dd'),
        label: format(now, 'LLLL yyyy'),
      }
    case 'last_month': {
      const prev = subMonths(now, 1)
      return {
        from: format(startOfMonth(prev), 'yyyy-MM-dd'),
        to: format(endOfMonth(prev), 'yyyy-MM-dd'),
        label: format(prev, 'LLLL yyyy'),
      }
    }
    case 'custom':
      return {
        from: customFrom ?? format(startOfMonth(now), 'yyyy-MM-dd'),
        to: customTo ?? format(endOfMonth(now), 'yyyy-MM-dd'),
        label: `${customFrom ?? '?'} - ${customTo ?? '?'}`,
      }
    default:
      return {
        from: format(startOfMonth(now), 'yyyy-MM-dd'),
        to: format(endOfMonth(now), 'yyyy-MM-dd'),
        label: format(now, 'LLLL yyyy'),
      }
  }
}

// ─── Data fetching ────────────────────────────────────────────────────────

async function fetchHRData(dateFrom: string, dateTo: string, location: string) {
  // 1. Fetch all instructors
  const { data: instructors, error: instrError } = await supabase
    .from('instructors')
    .select('id, first_name, last_name, hourly_rate, is_active, location')
    .eq('is_active', true)

  if (instrError) throw instrError

  // 2. Fetch bookings in the period
  let q = supabase
    .from('bookings')
    .select(
      'id, instructor_id, instructor_snap, duration_hours, start_time, end_time, start_date, persons, total_price, currency, booking_status',
    )
    .gte('start_date', dateFrom)
    .lte('start_date', dateTo)
    .neq('booking_status', 'cancelled')

  if (location !== 'both') {
    q = q.eq('location', location)
  }

  const { data: bookings, error: bookError } = await q
  if (bookError) throw bookError

  return {
    instructors: (instructors ?? []) as InstructorRow[],
    bookings: (bookings ?? []) as RawBooking[],
  }
}

// ─── Expense localStorage helpers ─────────────────────────────────────────
// NOTE: Expenses stored in localStorage as a temporary solution.
// Should migrate to a Supabase table (e.g. `expenses`) when SQL access is available.

const EXPENSES_KEY = 'flh_expenses'

function loadExpenses(): Expense[] {
  if (typeof localStorage === 'undefined') return []
  try {
    const raw = localStorage.getItem(EXPENSES_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveExpenses(expenses: Expense[]) {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(EXPENSES_KEY, JSON.stringify(expenses))
}

// ─── CSV export ───────────────────────────────────────────────────────────

function generateSalaryCSV(
  salaries: InstructorSalary[],
  totalHours: number,
  totalCost: number,
  periodLabel: string,
): string {
  const lines: string[] = []
  lines.push(`Raport HR — ${periodLabel}`)
  lines.push(`Wygenerowano: ${format(new Date(), 'yyyy-MM-dd HH:mm')}`)
  lines.push('')
  lines.push('PODSUMOWANIE')
  lines.push(`Laczne godziny instruktorow;${totalHours}`)
  lines.push(`Laczny koszt wynagrodzen;${totalCost}`)
  lines.push(`Srednia stawka;${salaries.length > 0 ? Math.round(totalCost / Math.max(totalHours, 1)) : 0}`)
  lines.push(`Aktywni instruktorzy;${salaries.length}`)
  lines.push('')
  lines.push('Instruktor;Godziny;Stawka/h;Lekcje;Wynagrodzenie;Bonus;Razem;Przychod PLN;Przychod EUR')
  salaries.forEach((s) => {
    lines.push(
      `${s.name};${s.hours};${s.rate ?? 'brak'};${s.lessons};${s.salary};${s.bonus};${s.total};${s.revenuePLN};${s.revenueEUR}`,
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
    try {
      const Sharing = require('expo-sharing')
      const FileSystem = require('expo-file-system')
      const path = FileSystem.documentDirectory + filename
      FileSystem.writeAsStringAsync(path, csv, { encoding: FileSystem.EncodingType.UTF8 }).then(() => {
        Sharing.shareAsync(path)
      })
    } catch {
      console.warn('Sharing not available')
    }
  }
}

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

// ─── HR Screen ────────────────────────────────────────────────────────────

export default function HRScreen() {
  const router = useRouter()
  const { session, selectedLocation, userRole } = useAuth()
  const userEmail = session?.user?.email?.toLowerCase() ?? ''

  // Owner/admin guard
  if (userRole !== 'admin' && !isOwnerEmail(userEmail, userRole)) {
    return (
      <View style={st.centered}>
        <Ionicons name="lock-closed-outline" size={48} color={C.textMuted} />
        <Text style={st.accessDenied}>Brak dostepu</Text>
        <Text style={st.accessDeniedSub}>Tylko wlasciciele maja dostep do HR.</Text>
        <TouchableOpacity onPress={() => router.back()} style={st.backLinkBtn}>
          <Text style={st.backLinkText}>Wstecz</Text>
        </TouchableOpacity>
      </View>
    )
  }

  const [period, setPeriod] = useState<PeriodKey>('this_month')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [activeTab, setActiveTab] = useState<TabKey>('salary')
  const [bonuses, setBonuses] = useState<Record<string, { amount: number; note: string }>>({})
  const [viewMode, setViewMode] = useState<ViewMode>(() => getViewMode('hr'))

  // Expense state
  const [expenses, setExpenses] = useState<Expense[]>(() => loadExpenses())
  const [showExpenseForm, setShowExpenseForm] = useState(false)
  const [newExpense, setNewExpense] = useState({
    amount: '',
    category: 'inne' as string,
    description: '',
  })

  const range = useMemo(() => getPeriodRange(period, customFrom, customTo), [period, customFrom, customTo])

  const { data, isLoading, isError } = useQuery({
    queryKey: ['hr-data', range.from, range.to, selectedLocation],
    queryFn: () => fetchHRData(range.from, range.to, selectedLocation),
    staleTime: 30000,
  })

  // Compute salary table
  const salaryTable = useMemo((): InstructorSalary[] => {
    if (!data) return []

    const { instructors, bookings } = data

    // Build a map from instructor_id to bookings
    const instrBookingMap = new Map<string, RawBooking[]>()
    bookings.forEach((b) => {
      if (b.instructor_id) {
        const arr = instrBookingMap.get(b.instructor_id) ?? []
        arr.push(b)
        instrBookingMap.set(b.instructor_id, arr)
      }
    })

    return instructors
      .map((instr): InstructorSalary => {
        const instrBookings = instrBookingMap.get(instr.id) ?? []
        // CRITICAL: instructor_hours = duration of each booking, NOT multiplied by persons
        const hours = instrBookings.reduce((sum, b) => sum + getDurationHours(b), 0)
        const roundedHours = Math.round(hours * 10) / 10
        const lessons = instrBookings.length
        const rate = instr.hourly_rate
        const salary = rate != null ? roundedHours * rate : 0
        const bonus = bonuses[instr.id]?.amount ?? 0
        const bonusNote = bonuses[instr.id]?.note ?? ''
        const total = salary + bonus

        const revenuePLN = instrBookings
          .filter((b) => b.currency === 'PLN')
          .reduce((s, b) => s + Number(b.total_price || 0), 0)
        const revenueEUR = instrBookings
          .filter((b) => b.currency === 'EUR')
          .reduce((s, b) => s + Number(b.total_price || 0), 0)

        return {
          id: instr.id,
          name: `${instr.first_name} ${instr.last_name}`,
          hours: roundedHours,
          lessons,
          rate,
          salary: Math.round(salary),
          bonus,
          bonusNote,
          total: Math.round(total),
          revenuePLN,
          revenueEUR,
        }
      })
      .filter((s) => s.lessons > 0 || s.rate != null)
      .sort((a, b) => b.hours - a.hours)
  }, [data, bonuses])

  const totalHours = salaryTable.reduce((s, i) => s + i.hours, 0)
  const totalCost = salaryTable.reduce((s, i) => s + i.total, 0)
  const totalSalaryOnly = salaryTable.reduce((s, i) => s + i.salary, 0)
  const activeInstructors = salaryTable.filter((i) => i.lessons > 0).length
  const avgRate =
    totalHours > 0
      ? Math.round(totalSalaryOnly / totalHours)
      : 0

  // Expenses filtered by period
  const periodExpenses = useMemo(() => {
    return expenses.filter((e) => e.date >= range.from && e.date <= range.to)
  }, [expenses, range])

  const totalExpenses = periodExpenses.reduce((s, e) => s + e.amount, 0)

  // Revenue from bookings (all in period, not just instructor-assigned)
  const totalRevenuePLN = useMemo(() => {
    if (!data) return 0
    return data.bookings
      .filter((b) => b.currency === 'PLN')
      .reduce((s, b) => s + Number(b.total_price || 0), 0)
  }, [data])

  const totalRevenueEUR = useMemo(() => {
    if (!data) return 0
    return data.bookings
      .filter((b) => b.currency === 'EUR')
      .reduce((s, b) => s + Number(b.total_price || 0), 0)
  }, [data])

  // Approximate combined revenue in PLN (EUR x 4.3)
  const totalRevenueCombined = totalRevenuePLN + totalRevenueEUR * 4.3
  const profitLoss = totalRevenueCombined - totalExpenses - totalCost

  // Handlers
  const handleBonusChange = useCallback((instrId: string, amount: string) => {
    setBonuses((prev) => ({
      ...prev,
      [instrId]: { ...prev[instrId], amount: Number(amount) || 0, note: prev[instrId]?.note ?? '' },
    }))
  }, [])

  const handleBonusNoteChange = useCallback((instrId: string, note: string) => {
    setBonuses((prev) => ({
      ...prev,
      [instrId]: { ...prev[instrId], amount: prev[instrId]?.amount ?? 0, note },
    }))
  }, [])

  const handleAddExpense = useCallback(() => {
    const amount = parseFloat(newExpense.amount)
    if (isNaN(amount) || amount <= 0) {
      if (Platform.OS === 'web') {
        window.alert('Podaj poprawna kwote')
      }
      return
    }
    const expense: Expense = {
      id: Date.now().toString(),
      date: format(new Date(), 'yyyy-MM-dd'),
      amount,
      category: newExpense.category,
      description: newExpense.description,
      created_by: userEmail,
    }
    const updated = [expense, ...expenses]
    setExpenses(updated)
    saveExpenses(updated)
    setNewExpense({ amount: '', category: 'inne', description: '' })
    setShowExpenseForm(false)
  }, [newExpense, expenses, userEmail])

  const handleDeleteExpense = useCallback(
    (id: string) => {
      const updated = expenses.filter((e) => e.id !== id)
      setExpenses(updated)
      saveExpenses(updated)
    },
    [expenses],
  )

  const handleExportCSV = useCallback(() => {
    const csv = generateSalaryCSV(salaryTable, totalHours, totalCost, range.label)
    const filename = `flh-hr-${format(new Date(), 'yyyy-MM-dd')}.csv`
    downloadCSV(csv, filename)
  }, [salaryTable, totalHours, totalCost, range.label])

  return (
    <View style={st.root}>
      {/* Header */}
      <View style={st.header}>
        <TouchableOpacity onPress={() => router.back()} style={st.backBtn} activeOpacity={0.7}>
          <Ionicons name="chevron-back" size={20} color={C.textSec} />
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={st.headerTitle}>HR & Wynagrodzenia</Text>
          <Text style={st.headerSub}>Godziny pracy, stawki, koszty</Text>
        </View>
        <ViewToggle mode={viewMode} onChange={(m) => { setViewMode(m); saveViewMode('hr', m) }} />
        <TouchableOpacity onPress={handleExportCSV} style={st.exportBtn} activeOpacity={0.7} disabled={!data}>
          <Ionicons name="download-outline" size={16} color={data ? C.primary : C.textMuted} />
          <Text style={[st.exportBtnText, { color: data ? C.primary : C.textMuted }]}>CSV</Text>
        </TouchableOpacity>
      </View>

      {/* Period selector */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={st.chipsScroll}
        contentContainerStyle={st.chipsContent}
      >
        {([
          { key: 'this_month' as PeriodKey, label: 'Ten miesiac' },
          { key: 'last_month' as PeriodKey, label: 'Ostatni miesiac' },
          { key: 'custom' as PeriodKey, label: 'Zakres' },
        ]).map((r) => {
          const isActive = period === r.key
          return (
            <TouchableOpacity
              key={r.key}
              onPress={() => setPeriod(r.key)}
              activeOpacity={0.7}
              style={[st.chip, isActive && st.chipActive]}
            >
              <Text style={[st.chipText, isActive && st.chipTextActive]}>{r.label}</Text>
            </TouchableOpacity>
          )
        })}
      </ScrollView>

      {/* Custom range inputs */}
      {period === 'custom' && (
        <View style={st.customRangeRow}>
          <TextInput
            style={st.dateInput}
            placeholder="Od (yyyy-mm-dd)"
            placeholderTextColor={C.textMuted}
            value={customFrom}
            onChangeText={setCustomFrom}
          />
          <Text style={st.dateInputSep}>-</Text>
          <TextInput
            style={st.dateInput}
            placeholder="Do (yyyy-mm-dd)"
            placeholderTextColor={C.textMuted}
            value={customTo}
            onChangeText={setCustomTo}
          />
        </View>
      )}

      {/* Tabs */}
      <View style={st.tabRow}>
        <TouchableOpacity
          onPress={() => setActiveTab('salary')}
          style={[st.tabBtn, activeTab === 'salary' && st.tabBtnActive]}
          activeOpacity={0.7}
        >
          <Ionicons name="people-outline" size={14} color={activeTab === 'salary' ? C.primary : C.textMuted} />
          <Text style={[st.tabText, activeTab === 'salary' && st.tabTextActive]}>Wynagrodzenia</Text>
        </TouchableOpacity>
        <TouchableOpacity
          onPress={() => setActiveTab('expenses')}
          style={[st.tabBtn, activeTab === 'expenses' && st.tabBtnActive]}
          activeOpacity={0.7}
        >
          <Ionicons name="receipt-outline" size={14} color={activeTab === 'expenses' ? C.primary : C.textMuted} />
          <Text style={[st.tabText, activeTab === 'expenses' && st.tabTextActive]}>Koszty</Text>
        </TouchableOpacity>
      </View>

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
            {activeTab === 'salary' ? (
              <>
                {/* ── Summary Cards ─────────────────────────────── */}
                <View style={st.summaryGrid}>
                  <SummaryCard
                    label="Godziny instruktorow"
                    value={`${Math.round(totalHours * 10) / 10}h`}
                    color="#7c3aed"
                    icon="time-outline"
                    sub={`${activeInstructors} aktywnych`}
                  />
                  <SummaryCard
                    label="Koszt wynagrodzen"
                    value={`${totalCost.toLocaleString('pl-PL')} PLN`}
                    color={C.error}
                    icon="wallet-outline"
                    sub={totalSalaryOnly !== totalCost ? `w tym bonus: ${totalCost - totalSalaryOnly} PLN` : undefined}
                  />
                  <SummaryCard
                    label="Srednia stawka/h"
                    value={avgRate > 0 ? `${avgRate} PLN` : '-'}
                    color={C.accent}
                    icon="trending-up-outline"
                  />
                  <SummaryCard
                    label="Aktywni instruktorzy"
                    value={String(activeInstructors)}
                    color={C.primary}
                    icon="people-circle-outline"
                    sub={`z ${data.instructors.length} zatrudnionych`}
                  />
                </View>

                {/* ── Instructor Salary Table ──────────────────── */}
                <Text style={st.sectionTitle}>Tabela wynagrodzen</Text>
                {salaryTable.length === 0 ? (
                  <View style={st.emptyBox}>
                    <Ionicons name="document-text-outline" size={48} color={C.border} />
                    <Text style={st.emptyText}>Brak danych o lekcjach w tym okresie</Text>
                  </View>
                ) : (
                  <View style={viewMode === 'grid' ? st.instrGrid : undefined}>
                  {salaryTable.map((instr, idx) => (
                    <View key={instr.id} style={[st.instrCard, viewMode === 'grid' && st.instrCardGrid]}>
                      {/* Instructor header */}
                      <View style={st.instrHeader}>
                        <Text style={st.instrName}>{instr.name}</Text>
                        <Text style={[st.instrTotal, { color: instr.rate != null ? C.success : C.warning }]}>
                          {instr.rate != null ? `${instr.total.toLocaleString('pl-PL')} PLN` : 'Brak stawki'}
                        </Text>
                      </View>

                      {/* Stats row */}
                      <View style={st.instrStatsRow}>
                        <View style={st.instrStat}>
                          <Text style={st.instrStatLabel}>Godziny</Text>
                          <Text style={st.instrStatValue}>{instr.hours}h</Text>
                        </View>
                        <View style={st.instrStat}>
                          <Text style={st.instrStatLabel}>Stawka/h</Text>
                          <Text style={st.instrStatValue}>
                            {instr.rate != null ? `${instr.rate} PLN` : '-'}
                          </Text>
                        </View>
                        <View style={st.instrStat}>
                          <Text style={st.instrStatLabel}>Lekcje</Text>
                          <Text style={st.instrStatValue}>{instr.lessons}</Text>
                        </View>
                        <View style={st.instrStat}>
                          <Text style={st.instrStatLabel}>Pensja</Text>
                          <Text style={st.instrStatValue}>
                            {instr.rate != null ? `${instr.salary.toLocaleString('pl-PL')}` : '-'}
                          </Text>
                        </View>
                      </View>

                      {/* Revenue generated */}
                      {(instr.revenuePLN > 0 || instr.revenueEUR > 0) && (
                        <View style={st.instrRevenueRow}>
                          <Text style={st.instrRevenueLabel}>Wygenerowany przychod:</Text>
                          <Text style={st.instrRevenueValue}>
                            {instr.revenuePLN > 0 ? `${instr.revenuePLN.toLocaleString('pl-PL')} PLN` : ''}
                            {instr.revenuePLN > 0 && instr.revenueEUR > 0 ? ' + ' : ''}
                            {instr.revenueEUR > 0 ? `${instr.revenueEUR.toLocaleString('pl-PL')} EUR` : ''}
                          </Text>
                        </View>
                      )}

                      {/* Bonus/penalty input */}
                      <View style={st.bonusRow}>
                        <View style={st.bonusInputWrap}>
                          <Text style={st.bonusLabel}>Bonus/kara</Text>
                          <TextInput
                            style={st.bonusInput}
                            placeholder="0"
                            placeholderTextColor={C.textMuted}
                            keyboardType="numeric"
                            value={bonuses[instr.id]?.amount ? String(bonuses[instr.id].amount) : ''}
                            onChangeText={(v) => handleBonusChange(instr.id, v)}
                          />
                        </View>
                        <View style={st.bonusNoteWrap}>
                          <Text style={st.bonusLabel}>Notatka</Text>
                          <TextInput
                            style={st.bonusNoteInput}
                            placeholder="np. bonus za weekend"
                            placeholderTextColor={C.textMuted}
                            value={bonuses[instr.id]?.note ?? ''}
                            onChangeText={(v) => handleBonusNoteChange(instr.id, v)}
                          />
                        </View>
                      </View>
                    </View>
                  ))}
                  </View>
                )}
              </>
            ) : (
              <>
                {/* ── Expenses Tab ─────────────────────────────── */}

                {/* Profit/loss summary */}
                <View style={st.summaryGrid}>
                  <SummaryCard
                    label="Przychod (okres)"
                    value={
                      totalRevenuePLN > 0 || totalRevenueEUR > 0
                        ? `${totalRevenuePLN > 0 ? totalRevenuePLN.toLocaleString('pl-PL') + ' PLN' : ''}${totalRevenuePLN > 0 && totalRevenueEUR > 0 ? ' + ' : ''}${totalRevenueEUR > 0 ? totalRevenueEUR.toLocaleString('pl-PL') + ' EUR' : ''}`
                        : '0 PLN'
                    }
                    color={C.primary}
                    icon="cash-outline"
                  />
                  <SummaryCard
                    label="Koszty (wydatki + pensje)"
                    value={`${(totalExpenses + totalCost).toLocaleString('pl-PL')} PLN`}
                    color={C.error}
                    icon="remove-circle-outline"
                    sub={`Wydatki: ${totalExpenses.toLocaleString('pl-PL')} | Pensje: ${totalCost.toLocaleString('pl-PL')}`}
                  />
                  <SummaryCard
                    label="Wynik (zysk/strata)"
                    value={`${profitLoss >= 0 ? '+' : ''}${Math.round(profitLoss).toLocaleString('pl-PL')} PLN`}
                    color={profitLoss >= 0 ? C.success : C.error}
                    icon={profitLoss >= 0 ? 'trending-up-outline' : 'trending-down-outline'}
                    sub="EUR przeliczony x 4.3"
                  />
                  <SummaryCard
                    label="Wydatki (okres)"
                    value={`${totalExpenses.toLocaleString('pl-PL')} PLN`}
                    color={C.warning}
                    icon="receipt-outline"
                    sub={`${periodExpenses.length} pozycji`}
                  />
                </View>

                {/* Add expense button */}
                <TouchableOpacity
                  onPress={() => setShowExpenseForm(!showExpenseForm)}
                  style={st.addExpenseBtn}
                  activeOpacity={0.7}
                >
                  <Ionicons name={showExpenseForm ? 'close-outline' : 'add-outline'} size={18} color={C.primary} />
                  <Text style={st.addExpenseText}>{showExpenseForm ? 'Anuluj' : 'Dodaj wydatek'}</Text>
                </TouchableOpacity>

                {/* Add expense form */}
                {showExpenseForm && (
                  <View style={st.expenseForm}>
                    <Text style={st.expenseFormTitle}>Nowy wydatek</Text>

                    <Text style={st.expenseFieldLabel}>Kwota (PLN)</Text>
                    <TextInput
                      style={st.expenseInput}
                      placeholder="np. 150"
                      placeholderTextColor={C.textMuted}
                      keyboardType="numeric"
                      value={newExpense.amount}
                      onChangeText={(v) => setNewExpense((p) => ({ ...p, amount: v }))}
                    />

                    <Text style={st.expenseFieldLabel}>Kategoria</Text>
                    <View style={st.categoryRow}>
                      {EXPENSE_CATEGORIES.map((cat) => (
                        <TouchableOpacity
                          key={cat}
                          onPress={() => setNewExpense((p) => ({ ...p, category: cat }))}
                          style={[st.categoryChip, newExpense.category === cat && st.categoryChipActive]}
                          activeOpacity={0.7}
                        >
                          <Text
                            style={[st.categoryChipText, newExpense.category === cat && st.categoryChipTextActive]}
                          >
                            {EXPENSE_LABELS[cat]}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>

                    <Text style={st.expenseFieldLabel}>Opis</Text>
                    <TextInput
                      style={st.expenseInput}
                      placeholder="np. Wymiana trapezow"
                      placeholderTextColor={C.textMuted}
                      value={newExpense.description}
                      onChangeText={(v) => setNewExpense((p) => ({ ...p, description: v }))}
                    />

                    <TouchableOpacity onPress={handleAddExpense} style={st.saveExpenseBtn} activeOpacity={0.7}>
                      <Ionicons name="checkmark-outline" size={16} color="#fff" />
                      <Text style={st.saveExpenseText}>Zapisz wydatek</Text>
                    </TouchableOpacity>
                  </View>
                )}

                {/* Expense list */}
                <Text style={st.sectionTitle}>Wydatki w okresie</Text>
                {periodExpenses.length === 0 ? (
                  <View style={st.emptyBox}>
                    <Ionicons name="receipt-outline" size={48} color={C.border} />
                    <Text style={st.emptyText}>Brak wydatkow w tym okresie</Text>
                    <Text style={st.emptySub}>Dodaj pierwszy wydatek przyciskiem powyzej.</Text>
                  </View>
                ) : (
                  periodExpenses.map((exp) => (
                    <View key={exp.id} style={st.expenseItem}>
                      <View style={st.expenseItemLeft}>
                        <View style={st.expenseItemTop}>
                          <View style={st.expenseCatBadge}>
                            <Text style={st.expenseCatText}>{EXPENSE_LABELS[exp.category] ?? exp.category}</Text>
                          </View>
                          <Text style={st.expenseDate}>{exp.date}</Text>
                        </View>
                        {exp.description ? <Text style={st.expenseDesc}>{exp.description}</Text> : null}
                      </View>
                      <View style={st.expenseItemRight}>
                        <Text style={st.expenseAmount}>{exp.amount.toLocaleString('pl-PL')} PLN</Text>
                        <TouchableOpacity onPress={() => handleDeleteExpense(exp.id)} activeOpacity={0.7}>
                          <Ionicons name="trash-outline" size={16} color={C.error} />
                        </TouchableOpacity>
                      </View>
                    </View>
                  ))
                )}

                {/* Local storage notice */}
                <View style={st.noticeBox}>
                  <Ionicons name="information-circle-outline" size={16} color={C.textMuted} />
                  <Text style={st.noticeText}>
                    Wydatki sa przechowywane lokalnie w przegladarce. Po wyczyszczeniu danych przegladarki zostana
                    utracone. Docelowo dane beda w bazie danych.
                  </Text>
                </View>
              </>
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

  // Period chips
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

  // Custom range
  customRangeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 8,
    gap: 8,
  },
  dateInput: {
    flex: 1,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 13,
    color: C.text,
  },
  dateInputSep: { color: C.textMuted, fontSize: 14 },

  // Tabs
  tabRow: {
    flexDirection: 'row',
    marginHorizontal: 20,
    marginBottom: 4,
    gap: 8,
  },
  tabBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
  },
  tabBtnActive: {
    backgroundColor: C.primarySoft,
    borderColor: C.primary,
  },
  tabText: { color: C.textMuted, fontSize: 13, fontWeight: '600' },
  tabTextActive: { color: C.primary, fontWeight: '700' },

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

  // Instructor salary card
  instrGrid: {
    flexDirection: 'row' as any,
    flexWrap: 'wrap' as any,
    gap: 10,
  },
  instrCard: {
    backgroundColor: C.surface,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: C.border,
  },
  instrCardGrid: {
    width: '48%' as any,
    marginBottom: 0,
  },
  instrHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  instrName: { color: C.text, fontSize: 15, fontWeight: '700', flex: 1 },
  instrTotal: { fontSize: 16, fontWeight: '800' },

  instrStatsRow: {
    flexDirection: 'row',
    gap: 4,
    marginBottom: 10,
  },
  instrStat: {
    flex: 1,
    backgroundColor: C.surfaceHigh,
    borderRadius: 10,
    padding: 8,
    alignItems: 'center',
  },
  instrStatLabel: { color: C.textMuted, fontSize: 9, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.3 },
  instrStatValue: { color: C.text, fontSize: 13, fontWeight: '700', marginTop: 2 },

  instrRevenueRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: C.border + '60',
    marginBottom: 8,
  },
  instrRevenueLabel: { color: C.textMuted, fontSize: 11 },
  instrRevenueValue: { color: C.success, fontSize: 12, fontWeight: '700' },

  // Bonus inputs
  bonusRow: {
    flexDirection: 'row',
    gap: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: C.border + '60',
  },
  bonusInputWrap: { width: 100 },
  bonusLabel: { color: C.textMuted, fontSize: 10, fontWeight: '600', marginBottom: 4 },
  bonusInput: {
    backgroundColor: C.surfaceAlt,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    fontSize: 13,
    color: C.text,
    textAlign: 'center',
  },
  bonusNoteWrap: { flex: 1 },
  bonusNoteInput: {
    backgroundColor: C.surfaceAlt,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    fontSize: 13,
    color: C.text,
  },

  // Expense button
  addExpenseBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: C.primarySoft,
    borderWidth: 1,
    borderColor: C.primary + '30',
    marginBottom: 16,
  },
  addExpenseText: { color: C.primary, fontSize: 14, fontWeight: '700' },

  // Expense form
  expenseForm: {
    backgroundColor: C.surface,
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: C.primary + '40',
  },
  expenseFormTitle: { color: C.text, fontSize: 15, fontWeight: '700', marginBottom: 12 },
  expenseFieldLabel: { color: C.textMuted, fontSize: 11, fontWeight: '600', marginBottom: 4, marginTop: 8 },
  expenseInput: {
    backgroundColor: C.surfaceAlt,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 14,
    color: C.text,
  },
  categoryRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 4 },
  categoryChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.surfaceHigh,
  },
  categoryChipActive: {
    borderColor: C.primary,
    backgroundColor: C.primarySoft,
  },
  categoryChipText: { color: C.textSec, fontSize: 12, fontWeight: '500' },
  categoryChipTextActive: { color: C.primary, fontWeight: '700' },
  saveExpenseBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    marginTop: 16,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: C.primary,
  },
  saveExpenseText: { color: '#fff', fontSize: 14, fontWeight: '700' },

  // Expense list items
  expenseItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: C.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: C.border,
  },
  expenseItemLeft: { flex: 1 },
  expenseItemTop: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4 },
  expenseCatBadge: {
    backgroundColor: C.warningSoft,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  expenseCatText: { color: C.warning, fontSize: 10, fontWeight: '700' },
  expenseDate: { color: C.textMuted, fontSize: 11 },
  expenseDesc: { color: C.textSec, fontSize: 13, marginTop: 2 },
  expenseItemRight: { alignItems: 'flex-end', gap: 6 },
  expenseAmount: { color: C.error, fontSize: 14, fontWeight: '700' },

  // Notice
  noticeBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: C.surfaceAlt,
    borderRadius: 12,
    padding: 12,
    marginTop: 16,
  },
  noticeText: { color: C.textMuted, fontSize: 11, flex: 1, lineHeight: 16 },

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
