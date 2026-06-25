export const AVATAR_PRESETS = Array.from({ length: 9 }, (_, index) => ({
  src: `/img/avatars/avatar-3d-${String(index + 1).padStart(2, '0')}.png`,
  label: `기본 프로필 ${index + 1}`,
}));

export function avatarPresetForIndex(index) {
  return AVATAR_PRESETS[index % AVATAR_PRESETS.length].src;
}
