// Owner check — uses admin role instead of hardcoded email list
// Any user with 'admin' role is treated as owner
export function isOwnerEmail(email: string | null | undefined, userRole: string | null): boolean {
  return userRole === 'admin'
}
