import { isOwnerEmail } from '@/lib/owner'
import { ScrollView, StyleSheet, Text, TouchableOpacity, View, Platform } from 'react-native'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useAuth } from '@/contexts/AuthContext'
import { C } from '@/constants/Colors'

// ─── Menu item ─────────────────────────────────────────────────────────────

function MenuItem({
  icon,
  label,
  sublabel,
  onPress,
  accent,
}: {
  icon: React.ComponentProps<typeof Ionicons>['name']
  label: string
  sublabel?: string
  onPress: () => void
  accent?: string
}) {
  const color = accent ?? C.textSec
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      style={s.menuItem}
    >
      <View style={[s.menuIcon, { backgroundColor: `${color}20` }]}>
        <Ionicons name={icon} size={18} color={color} />
      </View>
      <View style={s.menuText}>
        <Text style={s.menuLabel}>{label}</Text>
        {sublabel && <Text style={s.menuSublabel}>{sublabel}</Text>}
      </View>
      <Ionicons name="chevron-forward" size={16} color={C.border} />
    </TouchableOpacity>
  )
}

// ─── More Screen ───────────────────────────────────────────────────────────


export default function MoreScreen() {
  const { userRole, selectedLocation, signOut, session } = useAuth()
  const router = useRouter()
  const isOwner = userRole === 'admin' || isOwnerEmail(session?.user?.email, userRole)

  const locationLabel =
    selectedLocation === 'hel' ? 'Hel, Poland' : selectedLocation === 'hurghada' ? 'Hurghada, Egypt' : 'All locations'

  return (
    <View style={s.container}>
      {/* Header */}
      <View style={s.header}>
        <Text style={s.headerTitle}>Więcej</Text>
        <Text style={s.headerSub}>{session?.user?.email}</Text>
      </View>

      <ScrollView
        style={s.scroll}
        contentContainerStyle={{ paddingBottom: 40 }}
        showsVerticalScrollIndicator={true}
      >
        {/* Role card */}
        <View style={s.roleCard}>
          <View style={s.roleAvatar}>
            <Ionicons name="shield-checkmark-outline" size={22} color={C.primary} />
          </View>
          <View>
            <Text style={s.roleTitle}>{userRole ?? 'Staff'}</Text>
            <Text style={s.roleLocation}>{locationLabel}</Text>
          </View>
        </View>

        {/* Management section */}
        <Text style={s.sectionLabel}>Zarządzanie</Text>
        <View style={s.card}>
          <MenuItem
            icon="grid-outline"
            label="Usługi"
            sublabel="Katalog usług i cennik"
            onPress={() => router.push('/(app)/more/services')}
            accent="#0ea5e9"
          />
          <MenuItem
            icon="cube-outline"
            label="Sprzet"
            sublabel="Inwentarz, serwis, wypozyczenia"
            onPress={() => router.push('/(app)/more/equipment')}
            accent="#0891b2"
          />
          <MenuItem
            icon="card-outline"
            label="Płatności"
            sublabel="Zaległości i historia"
            onPress={() => router.push('/(app)/more/payments')}
            accent="#22c55e"
          />
          <MenuItem
            icon="layers-outline"
            label="Pakiety"
            sublabel="Pakiety sesji"
            onPress={() => router.push('/(app)/more/packages')}
            accent="#a855f7"
          />
          <MenuItem
            icon="calendar-number-outline"
            label="Dostepnosc instruktorow"
            sublabel="Godziny pracy i dni wolne"
            onPress={() => router.push('/(app)/more/availability')}
            accent="#0891b2"
          />
          {isOwner && (
            <MenuItem
              icon="analytics-outline"
              label="Finanse & Analityka"
              sublabel="Przychody, godziny, statystyki"
              onPress={() => router.push('/(app)/more/analytics')}
              accent="#6366f1"
            />
          )}
          {isOwner && (
            <MenuItem
              icon="bar-chart-outline"
              label="Raporty wizualne"
              sublabel="Wykresy, porownania, wykorzystanie"
              onPress={() => router.push('/(app)/more/reports')}
              accent="#0ea5e9"
            />
          )}
          {isOwner && (
            <MenuItem
              icon="people-circle-outline"
              label="HR & Wynagrodzenia"
              sublabel="Godziny pracy, stawki, wyplaty"
              onPress={() => router.push('/(app)/more/hr')}
              accent="#ec4899"
            />
          )}
        </View>

        {/* Szkolenia / certyfikaty */}
        <Text style={s.sectionLabel}>Szkolenia</Text>
        <View style={s.card}>
          <MenuItem
            icon="ribbon-outline"
            label="PZKite & Certyfikaty"
            sublabel="Kursy instruktorskie, daty, linki"
            onPress={() => router.push('/(app)/more/pzkite')}
            accent="#f59e0b"
          />
        </View>

        {/* Account section */}
        <Text style={s.sectionLabel}>Konto</Text>
        <View style={[s.card, { marginBottom: 20 }]}>
          <MenuItem
            icon="settings-outline"
            label="Ustawienia"
            sublabel="Lokalizacja, powiadomienia"
            onPress={() => router.push('/(app)/more/settings')}
            accent={C.textSec}
          />
        </View>

        {/* Sign out */}
        <TouchableOpacity
          onPress={signOut}
          activeOpacity={0.8}
          style={s.signOutBtn}
        >
          <Ionicons name="log-out-outline" size={18} color={C.error} />
          <Text style={s.signOutText}>Wyloguj się</Text>
        </TouchableOpacity>

        {/* Version */}
        <Text style={s.version}>SurfIQ v1.0.0 · {process.env.EXPO_PUBLIC_SCHOOL_NAME || 'FUN like HEL'}</Text>
      </ScrollView>
    </View>
  )
}

const s = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: C.bg,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'web' ? 24 : 56,
    paddingBottom: 16,
  },
  headerTitle: {
    color: C.text,
    fontSize: 24,
    fontWeight: '700',
  },
  headerSub: {
    color: C.textSec,
    fontSize: 14,
    marginTop: 4,
  },
  scroll: {
    flex: 1,
    paddingHorizontal: 20,
  },
  roleCard: {
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
    flexDirection: 'row',
    alignItems: 'center',
  },
  roleAvatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: `${C.primary}20`,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  roleTitle: {
    color: C.text,
    fontSize: 16,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  roleLocation: {
    color: C.textMuted,
    fontSize: 14,
  },
  sectionLabel: {
    color: C.textSec,
    fontSize: 11,
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 8,
  },
  card: {
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 16,
    paddingHorizontal: 16,
    marginBottom: 20,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: `${C.border}60`,
  },
  menuIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  menuText: {
    flex: 1,
  },
  menuLabel: {
    color: C.text,
    fontSize: 16,
  },
  menuSublabel: {
    color: C.textSec,
    fontSize: 12,
    marginTop: 2,
  },
  signOutBtn: {
    backgroundColor: `${C.error}18`,
    borderWidth: 1,
    borderColor: `${C.error}50`,
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  signOutText: {
    color: C.error,
    fontSize: 16,
    fontWeight: '500',
    marginLeft: 8,
  },
  version: {
    color: C.textMuted,
    fontSize: 12,
    textAlign: 'center',
    marginTop: 24,
  },
})
