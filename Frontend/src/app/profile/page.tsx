import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Input, Select, Textarea } from "@/components/ui/form-controls";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import { Tabs } from "@/components/ui/tabs";
import { getApiErrorMessage, getProfile, toApiResult } from "@/lib/api";
import type { CandidateProfile, ProfileClaim, TargetTitle } from "@/lib/api";
import {
  applyAcceptedTitlesAction,
  applySearchStrategyAction,
  generateSearchStrategyAction,
  generateTargetTitlesAction,
  importResumeAction,
  setProfileClaimStatusAction,
  setTargetTitleStatusAction,
  updateProfileAction,
} from "./actions";

type ProfilePageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function ProfilePage({ searchParams }: ProfilePageProps) {
  const params = await searchParams;
  const notice = getSearchParam(params, "profile_notice");
  const error = getSearchParam(params, "profile_error");
  const activeTab = getSearchParam(params, "tab") || "overview";
  const profileResult = await toApiResult(getProfile());
  const profile = profileResult.ok ? profileResult.data : null;

  const acceptedTitles = profile?.target_titles.filter((title) => title.status === "accepted") ?? [];
  const unconfirmedClaims = profile?.claims.filter((claim) => claim.status === "unconfirmed") ?? [];
  const confirmedClaims = profile?.claims.filter((claim) => claim.status === "confirmed") ?? [];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Profile"
        eyebrow="Candidate"
        description="Build reusable candidate context for source discovery, job matching, and notification decisions."
        actions={
          <form action={generateTargetTitlesAction}>
            <Button type="submit" variant="primary">
              Generate titles
            </Button>
          </form>
        }
      />

      {notice ? <SystemBanner tone="success">{notice}</SystemBanner> : null}

      {error ? <ErrorState title="Profile action failed" message={error} /> : null}

      {!profileResult.ok ? (
        <ErrorState
          title="Backend API is unavailable"
          message="Profile could not be loaded."
          detail={getApiErrorMessage(profileResult.error)}
        />
      ) : null}

      {profile ? (
        <>
          <div className="grid gap-3 md:grid-cols-5">
            <MetricCard label="Complete" value={`${profile.profile_completeness_score}%`} detail="Profile readiness" />
            <MetricCard label="Skills" value={profile.skills.length} detail="Profile terms" />
            <MetricCard label="Target titles" value={profile.target_titles.length} detail={`${acceptedTitles.length} accepted`} />
            <MetricCard label="Claims" value={profile.claims.length} detail={`${unconfirmedClaims.length} unconfirmed`} />
            <MetricCard label="Confirmed" value={confirmedClaims.length} detail="Approved proof points" />
          </div>

          <Tabs
            items={[
              { href: "/profile?tab=overview", label: "Overview", active: activeTab === "overview" },
              { href: "/profile?tab=resume", label: "Resume", active: activeTab === "resume" },
              { href: "/profile?tab=fields", label: "Fields", active: activeTab === "fields" },
              { href: "/profile?tab=files", label: "Files", active: activeTab === "files" },
              { href: "/profile?tab=titles", label: "Target Titles", active: activeTab === "titles" },
              { href: "/profile?tab=claims", label: "Claims", active: activeTab === "claims" },
              { href: "/profile?tab=strategy", label: "Search Strategy", active: activeTab === "strategy" },
            ]}
          />

          {activeTab === "overview" ? <ProfileDataPanel profile={profile} /> : null}
          {activeTab === "resume" ? <ResumeImportPanel /> : null}
          {activeTab === "fields" ? <ManualProfileForm profile={profile} /> : null}
          {activeTab === "files" ? <MarkdownEditors profile={profile} /> : null}
          {activeTab === "titles" ? <TargetTitlesPanel titles={profile.target_titles} /> : null}
          {activeTab === "claims" ? <ClaimsPanel claims={profile.claims} /> : null}
          {activeTab === "strategy" ? <SearchStrategyPanel profile={profile} /> : null}
        </>
      ) : null}
    </div>
  );
}

function ManualProfileForm({ profile }: { profile: CandidateProfile }) {
  return (
    <PageSection title="Manual profile">
      <form action={updateProfileAction} className="grid gap-3 p-4 md:grid-cols-2">
        <TextInput label="Full name" name="full_name" defaultValue={profile.full_name} />
        <TextInput label="Headline" name="headline" defaultValue={profile.headline} />
        <TextInput label="Location" name="location" defaultValue={profile.location} />
        <label className="block">
          <span className="text-xs font-medium text-slate-600">Remote preference</span>
          <Select
            name="remote_preference"
            defaultValue={profile.remote_preference || "any"}
          >
            <option value="any">Any</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">Onsite</option>
          </Select>
        </label>
        <TextInput label="Target locations" name="target_locations" defaultValue={profile.target_locations.join(", ")} />
        <TextInput label="Preferred work modes" name="preferred_work_modes" defaultValue={profile.preferred_work_modes.join(", ")} />
        <TextInput label="Skills" name="skills" defaultValue={profile.skills.join(", ")} />
        <TextInput label="Compensation" name="compensation_expectation" defaultValue={profile.compensation_expectation} />
        <TextInput label="GitHub" name="github_url" defaultValue={profile.links.github || ""} />
        <TextInput label="LinkedIn" name="linkedin_url" defaultValue={profile.links.linkedin || ""} />
        <TextInput label="Portfolio" name="portfolio_url" defaultValue={profile.links.portfolio || ""} />
        <label className="block md:col-span-2">
          <span className="text-xs font-medium text-slate-600">Summary</span>
          <Textarea
            name="summary"
            defaultValue={profile.summary}
            rows={4}
          />
        </label>
        <label className="block md:col-span-2">
          <span className="text-xs font-medium text-slate-600">Dealbreakers</span>
          <Textarea
            name="dealbreakers"
            defaultValue={profile.dealbreakers}
            rows={3}
          />
        </label>
        <label className="block md:col-span-2">
          <span className="text-xs font-medium text-slate-600">Role framing</span>
          <Textarea
            name="role_framing"
            defaultValue={profile.role_framing}
            rows={3}
          />
        </label>
        <div className="flex justify-end md:col-span-2">
          <Button type="submit" variant="primary">
            Save profile
          </Button>
        </div>
      </form>
    </PageSection>
  );
}

function ResumeImportPanel() {
  return (
    <PageSection title="Resume import">
      <form action={importResumeAction} className="space-y-3 p-4">
        <label className="block">
          <span className="text-xs font-medium text-slate-600">Resume or CV text</span>
          <Textarea
            name="resume_text"
            rows={16}
            className="font-mono text-xs leading-5"
          />
        </label>
        <Button type="submit" variant="primary">
          Import resume
        </Button>
      </form>
    </PageSection>
  );
}

function MarkdownEditors({ profile }: { profile: CandidateProfile }) {
  return (
    <PageSection title="Markdown files">
      <form action={updateProfileAction} className="grid gap-4 p-4 xl:grid-cols-3">
        <HiddenProfileFields profile={profile} />
        <label className="block">
          <span className="text-xs font-medium text-slate-600">cv.md</span>
          <textarea
            name="cv_markdown"
            defaultValue={profile.cv_markdown}
            rows={18}
            className="mt-1 w-full resize-y rounded-md border border-slate-300 bg-slate-950 px-3 py-2 font-mono text-xs leading-5 text-slate-50 outline-none focus:ring-2 focus:ring-slate-300"
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-slate-600">profile.md</span>
          <textarea
            name="profile_markdown"
            defaultValue={profile.profile_markdown}
            rows={18}
            className="mt-1 w-full resize-y rounded-md border border-slate-300 bg-slate-950 px-3 py-2 font-mono text-xs leading-5 text-slate-50 outline-none focus:ring-2 focus:ring-slate-300"
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-slate-600">profile.yml</span>
          <textarea
            name="profile_yml"
            defaultValue={profile.profile_yml}
            rows={18}
            className="mt-1 w-full resize-y rounded-md border border-slate-300 bg-slate-950 px-3 py-2 font-mono text-xs leading-5 text-slate-50 outline-none focus:ring-2 focus:ring-slate-300"
          />
        </label>
        <div className="flex justify-end xl:col-span-3">
          <Button type="submit" variant="primary">
            Save markdown
          </Button>
        </div>
      </form>
    </PageSection>
  );
}

function HiddenProfileFields({ profile }: { profile: CandidateProfile }) {
  return (
    <>
      <input type="hidden" name="full_name" value={profile.full_name} />
      <input type="hidden" name="headline" value={profile.headline} />
      <input type="hidden" name="location" value={profile.location} />
      <input type="hidden" name="remote_preference" value={profile.remote_preference} />
      <input type="hidden" name="target_locations" value={profile.target_locations.join(", ")} />
      <input type="hidden" name="preferred_work_modes" value={profile.preferred_work_modes.join(", ")} />
      <input type="hidden" name="skills" value={profile.skills.join(", ")} />
      <input type="hidden" name="summary" value={profile.summary} />
      <input type="hidden" name="dealbreakers" value={profile.dealbreakers} />
      <input type="hidden" name="compensation_expectation" value={profile.compensation_expectation} />
      <input type="hidden" name="role_framing" value={profile.role_framing} />
      <input type="hidden" name="github_url" value={profile.links.github || ""} />
      <input type="hidden" name="linkedin_url" value={profile.links.linkedin || ""} />
      <input type="hidden" name="portfolio_url" value={profile.links.portfolio || ""} />
    </>
  );
}

function ProfileDataPanel({ profile }: { profile: CandidateProfile }) {
  return (
    <PageSection title="Structured profile">
      <div className="grid gap-4 p-4 lg:grid-cols-3">
        <StructuredList
          title="Proof points"
          empty="No proof points extracted yet."
          items={profile.proof_points.slice(0, 8).map((point) => getItemString(point, "text"))}
        />
        <StructuredList
          title="Skill inventory"
          empty="No skill inventory yet."
          items={profile.skill_inventory.slice(0, 12).map((item) => {
            const skill = getItemString(item, "skill");
            const confidence = getItemString(item, "confidence");
            return confidence ? `${skill} (${confidence}%)` : skill;
          })}
        />
        <StructuredList
          title="Career timeline"
          empty="No timeline items extracted yet."
          items={profile.career_timeline.slice(0, 8).map((item) => getItemString(item, "label"))}
        />
      </div>
    </PageSection>
  );
}

function SearchStrategyPanel({ profile }: { profile: CandidateProfile }) {
  const strategy = profile.search_strategy;

  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-950">Search strategy</h2>
          <p className="mt-1 text-xs text-slate-500">
            Reviewable filters for company tracking and job ranking.
          </p>
        </div>
        <div className="flex gap-2">
          <form action={generateSearchStrategyAction}>
            <Button type="submit" size="sm">
              Generate
            </Button>
          </form>
          <form action={applySearchStrategyAction}>
            <Button
              type="submit"
              disabled={!strategy || strategy.target_title_keywords.length === 0}
              variant="primary"
              size="sm"
            >
              Apply to companies
            </Button>
          </form>
        </div>
      </div>
      {!strategy ? (
        <div className="px-4 py-5 text-sm text-slate-600">No search strategy generated yet.</div>
      ) : (
        <div className="grid gap-4 p-4 lg:grid-cols-3">
          <StructuredList title="Role families" empty="No role families." items={strategy.role_families} />
          <StructuredList title="Title keywords" empty="No title keywords." items={strategy.target_title_keywords} />
          <StructuredList title="Negative keywords" empty="No negative keywords." items={strategy.negative_keywords} />
          <StructuredList title="Seniority" empty="No seniority guidance." items={strategy.seniority_levels} />
          <StructuredList title="Locations" empty="No location strategy." items={strategy.location_keywords} />
          <StructuredList title="Work modes" empty="No work-mode strategy." items={strategy.work_mode_preferences} />
          {strategy.notes ? (
            <div className="lg:col-span-3 rounded-md bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-700">
              {strategy.notes}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

function StructuredList({
  title,
  empty,
  items,
}: {
  title: string;
  empty: string;
  items: string[];
}) {
  const visibleItems = items.filter(Boolean);
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase text-slate-500">{title}</h3>
      {visibleItems.length === 0 ? (
        <p className="mt-2 text-sm text-slate-600">{empty}</p>
      ) : (
        <ul className="mt-2 space-y-2 text-sm leading-5 text-slate-700">
          {visibleItems.map((item) => (
            <li key={item} className="rounded-md bg-slate-50 px-3 py-2">
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TargetTitlesPanel({ titles }: { titles: TargetTitle[] }) {
  const acceptedCount = titles.filter((title) => title.status === "accepted").length;

  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">Target titles</h2>
        <form action={applyAcceptedTitlesAction}>
          <Button
            type="submit"
            disabled={acceptedCount === 0}
            variant="primary"
            size="sm"
          >
            Apply accepted
          </Button>
        </form>
      </div>
      {titles.length === 0 ? (
        <div className="px-4 py-5 text-sm text-slate-600">No target titles yet.</div>
      ) : (
        <div className="divide-y divide-slate-100">
          {titles.map((title) => (
            <article key={title.id} className="px-4 py-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-medium text-slate-950">{title.title}</div>
                  <div className="mt-1 flex flex-wrap gap-2">
                    <StatusBadge tone={titleStatusTone(title.status)} withDot>
                      {title.status}
                    </StatusBadge>
                    <StatusBadge tone={fitTone(title.fit_bucket)}>{title.fit_bucket}</StatusBadge>
                    <span className="text-xs text-slate-500">
                      Confidence {title.confidence_score}% · knowledge {title.knowledge_accuracy}%
                    </span>
                  </div>
                  {title.evidence.length ? (
                    <div className="mt-2 text-xs leading-5 text-slate-600">
                      Evidence: {title.evidence.join(", ")}
                    </div>
                  ) : null}
                </div>
                <div className="flex gap-2">
                  <TargetStatusButton titleId={title.id} status="accepted" label="Accept" />
                  <TargetStatusButton titleId={title.id} status="rejected" label="Reject" />
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function ClaimsPanel({ claims }: { claims: ProfileClaim[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">Claims</h2>
      </div>
      {claims.length === 0 ? (
        <div className="px-4 py-5 text-sm text-slate-600">No claims extracted yet.</div>
      ) : (
        <div className="divide-y divide-slate-100">
          {claims.slice(0, 40).map((claim) => (
            <article key={claim.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-medium leading-6 text-slate-950">
                    {claim.text}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-2">
                    <StatusBadge tone={claimStatusTone(claim.status)} withDot>
                      {claim.status}
                    </StatusBadge>
                    <StatusBadge tone="neutral">{claim.claim_type}</StatusBadge>
                  </div>
                </div>
                <div className="flex shrink-0 gap-2">
                  <ClaimStatusButton claimId={claim.id} status="confirmed" label="Confirm" />
                  <ClaimStatusButton claimId={claim.id} status="rejected" label="Reject" />
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function TargetStatusButton({
  titleId,
  status,
  label,
}: {
  titleId: number;
  status: "accepted" | "rejected";
  label: string;
}) {
  return (
    <form action={setTargetTitleStatusAction}>
      <input type="hidden" name="title_id" value={titleId} />
      <input type="hidden" name="status" value={status} />
      <Button type="submit" size="sm">
        {label}
      </Button>
    </form>
  );
}

function ClaimStatusButton({
  claimId,
  status,
  label,
}: {
  claimId: number;
  status: "confirmed" | "rejected";
  label: string;
}) {
  return (
    <form action={setProfileClaimStatusAction}>
      <input type="hidden" name="claim_id" value={claimId} />
      <input type="hidden" name="status" value={status} />
      <Button type="submit" size="sm">
        {label}
      </Button>
    </form>
  );
}

function TextInput({
  label,
  name,
  defaultValue,
}: {
  label: string;
  name: string;
  defaultValue: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <Input
        name={name}
        defaultValue={defaultValue}
      />
    </label>
  );
}

function titleStatusTone(status: string) {
  switch (status) {
    case "accepted":
      return "success" as const;
    case "rejected":
      return "neutral" as const;
    default:
      return "warning" as const;
  }
}

function fitTone(fitBucket: string) {
  switch (fitBucket) {
    case "core":
      return "success" as const;
    case "stretch":
      return "warning" as const;
    default:
      return "info" as const;
  }
}

function claimStatusTone(status: string) {
  switch (status) {
    case "confirmed":
      return "success" as const;
    case "rejected":
      return "neutral" as const;
    case "needs_edit":
      return "warning" as const;
    default:
      return "danger" as const;
  }
}

function getItemString(item: Record<string, unknown>, key: string) {
  const value = item[key];
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "";
}

function getSearchParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}
