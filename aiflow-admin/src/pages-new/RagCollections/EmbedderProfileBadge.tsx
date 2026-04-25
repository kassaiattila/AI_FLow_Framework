import { EMBEDDER_PROFILE_OPTIONS } from "./types";

interface Props {
  profileId: string | null;
}

export function EmbedderProfileBadge({ profileId }: Props) {
  const opt =
    EMBEDDER_PROFILE_OPTIONS.find((o) => o.value === profileId) ??
    EMBEDDER_PROFILE_OPTIONS[0];
  const label = profileId ?? "default";
  return (
    <span
      data-testid="rag-collections-profile-badge"
      data-profile={label}
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${opt.badgeClass}`}
    >
      {label}
    </span>
  );
}
