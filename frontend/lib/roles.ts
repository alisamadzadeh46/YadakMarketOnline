// Single source of truth for "where does this role's own area live".
// The header avatar, the /account guard and every «my panel» link all read
// this, so a user can never end up with two rival account homes.
export function homeForRole(role?: string) {
  if (role === "supplier" || role === "admin") return "/panel/supplier";
  if (role === "partner") return "/panel/partner";
  if (role === "shopkeeper") return "/panel/shop";
  return "/account";
}

/** Where the «profile» link for this role should point. */
export function profileHrefForRole(role?: string) {
  if (role === "supplier" || role === "admin") return "/panel/supplier/profile";
  if (role === "shopkeeper") return "/panel/shop/profile";
  if (role === "partner") return "/panel/partner";
  return "/account/profile";
}
