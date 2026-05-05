import Link from "next/link";
import { Button, ButtonLink } from "@/components/ui/button";
import { DetailDrawer } from "@/components/ui/detail-drawer";
import { ErrorState } from "@/components/ui/error-state";
import { Input, Select, Textarea } from "@/components/ui/form-controls";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import {
  getApiErrorMessage,
  listApplications,
  toApiResult,
} from "@/lib/api";
import type { ApplicationArtifact, ApplicationRecord } from "@/lib/api";
import {
  generateApplicationArtifactsAction,
  generateInterviewPrepAction,
  generateOfferSupportAction,
  setApplicationArtifactStatusAction,
  updateApplicationAction,
} from "./actions";

const statusGroups = [
  { key: "saved", label: "Saved" },
  { key: "applying", label: "Applying" },
  { key: "applied", label: "Applied" },
  { key: "interviewing", label: "Interviewing" },
  { key: "offer", label: "Offer" },
  { key: "rejected", label: "Rejected" },
  { key: "withdrawn", label: "Withdrawn" },
  { key: "skipped", label: "Skipped" },
];

type ApplicationsPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function ApplicationsPage({
  searchParams,
}: ApplicationsPageProps) {
  const params = await searchParams;
  const notice = getSearchParam(params, "applications_notice");
  const error = getSearchParam(params, "applications_error");
  const selectedApplicationId = Number(getSearchParam(params, "application_id"));
  const applicationsResult = await toApiResult(listApplications());
  const applications = applicationsResult.ok ? applicationsResult.data.results : [];
  const selectedApplication =
    (Number.isInteger(selectedApplicationId)
      ? applications.find((application) => application.id === selectedApplicationId)
      : undefined) ?? applications[0];
  const activeCount = applications.filter((application) =>
    ["saved", "applying", "applied", "interviewing"].includes(application.status),
  ).length;
  const followUpCount = applications.filter((application) => application.follow_up_at).length;
  const artifactCount = applications.reduce((total, application) => total + application.artifacts.length, 0);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Applications"
        eyebrow="Pipeline"
        description="Compact application lanes with a detail drawer for status, notes, follow-ups, generated artifacts, interview prep, and offer support."
        actions={
          <ButtonLink href="/">
            Open Today
          </ButtonLink>
        }
      />

      {notice ? <SystemBanner tone="success">{notice}</SystemBanner> : null}
      {error ? <ErrorState title="Application action failed" message={error} /> : null}

      {!applicationsResult.ok ? (
        <ErrorState
          title="Backend API is unavailable"
          message="Applications could not be loaded."
          detail={getApiErrorMessage(applicationsResult.error)}
        />
      ) : null}

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="Applications" value={applications.length} detail="Tracked roles" />
        <MetricCard label="Active" value={activeCount} detail="Still in play" />
        <MetricCard label="Follow-ups" value={followUpCount} detail="With next date" />
        <MetricCard label="Artifacts" value={artifactCount} detail="Prep drafts" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_500px]">
        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
          {statusGroups.map((group) => (
            <ApplicationLane
              key={group.key}
              label={group.label}
              status={group.key}
              applications={applications.filter((application) => application.status === group.key)}
              selectedApplication={selectedApplication}
            />
          ))}
        </div>
        <ApplicationDrawer application={selectedApplication} />
      </div>
    </div>
  );
}

function ApplicationLane({
  label,
  status,
  applications,
  selectedApplication,
}: {
  label: string;
  status: string;
  applications: ApplicationRecord[];
  selectedApplication?: ApplicationRecord;
}) {
  return (
    <PageSection
      title={label}
      actions={<StatusBadge tone={statusTone(status)}>{applications.length}</StatusBadge>}
      className="min-h-56"
    >
      {applications.length === 0 ? (
        <div className="px-3 py-4 text-sm text-slate-500">No roles in this lane.</div>
      ) : (
        <div className="space-y-3 p-3">
          {applications.map((application) => (
            <ApplicationCard
              key={application.id}
              application={application}
              selected={application.id === selectedApplication?.id}
            />
          ))}
        </div>
      )}
    </PageSection>
  );
}

function ApplicationCard({
  application,
  selected,
}: {
  application: ApplicationRecord;
  selected: boolean;
}) {
  return (
    <Link
      href={`/applications?application_id=${application.id}`}
      className={[
        "block rounded-md border p-3 transition hover:bg-slate-800",
        selected ? "border-indigo-300 bg-indigo-500/10" : "border-slate-800 bg-slate-950",
      ].join(" ")}
    >
      <div className="min-w-0">
        <div className="truncate font-medium leading-5 text-slate-50">
          {application.job_title}
        </div>
        <div className="mt-1 truncate text-xs text-slate-500">
          {application.company_name} - {application.location || "Location unknown"}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <StatusBadge tone={statusTone(application.status)} withDot>
          {labelize(application.status)}
        </StatusBadge>
        {application.follow_up_at ? (
          <span className="font-mono text-[11px] text-slate-600">
            {formatDateTime(application.follow_up_at)}
          </span>
        ) : null}
      </div>
      {application.next_action ? (
        <div className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">
          {application.next_action}
        </div>
      ) : null}
    </Link>
  );
}

function ApplicationDrawer({ application }: { application?: ApplicationRecord }) {
  if (!application) {
    return (
      <DetailDrawer title="No application selected" subtitle="Save a role or select an application card.">
        <p className="text-sm leading-6 text-slate-500">
          Status editing, notes, artifacts, prep, and offer support will appear here.
        </p>
      </DetailDrawer>
    );
  }

  return (
    <DetailDrawer
      eyebrow={`Applications / ${application.company_name}`}
      title={application.job_title}
      subtitle={`${application.location || "Location unknown"} - ${application.remote_policy || "Work mode unknown"}`}
      closeHref="/applications"
      footer={
        <ButtonLink href={application.apply_url} target="_blank" className="w-full">
          Open original role
        </ButtonLink>
      }
    >
      <div className="space-y-5">
        <form action={updateApplicationAction} className="space-y-3 rounded-lg border border-slate-800 bg-slate-950 p-4">
          <input type="hidden" name="application_id" value={application.id} />
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="text-xs font-medium text-slate-500">Status</span>
              <Select name="status" defaultValue={application.status}>
                {statusGroups.map((group) => (
                  <option key={group.key} value={group.key}>{group.label}</option>
                ))}
              </Select>
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-500">Follow-up date</span>
              <Input name="follow_up_at" type="date" defaultValue={dateInputValue(application.follow_up_at)} />
            </label>
          </div>
          <label className="block">
            <span className="text-xs font-medium text-slate-500">Next action</span>
            <Input name="next_action" defaultValue={application.next_action} placeholder="Follow up, tailor CV, prepare screen" />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-500">Internal notes</span>
            <Textarea name="notes" defaultValue={application.notes} rows={5} />
          </label>
          <Button type="submit" variant="primary">
            Save changes
          </Button>
        </form>

        <ApplicationArtifacts application={application} />
        <InterviewOfferPrep application={application} />
      </div>
    </DetailDrawer>
  );
}

function InterviewOfferPrep({ application }: { application: ApplicationRecord }) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-950">
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-slate-50">Interview and offer</div>
          <div className="mt-1 text-xs text-slate-500">Generated prep stays reviewable before use.</div>
        </div>
        <div className="flex gap-1">
          <PrepButton applicationId={application.id} action={generateInterviewPrepAction} label="Interview" />
          <PrepButton applicationId={application.id} action={generateOfferSupportAction} label="Offer" />
        </div>
      </div>
      <div className="grid gap-2 px-4 py-3 text-xs leading-5 text-slate-500">
        <div>
          <span className="font-semibold text-slate-300">Prep:</span>{" "}
          {application.interview_prep
            ? `${application.interview_prep.focus_areas.length} focus areas, ${application.interview_prep.gaps.length} gaps`
            : "Not generated"}
        </div>
        <div>
          <span className="font-semibold text-slate-300">Offer:</span>{" "}
          {application.offer_support
            ? `${application.offer_support.decision_criteria.length} criteria, ${application.offer_support.risk_flags.length} risk flags`
            : "Not generated"}
        </div>
      </div>
    </section>
  );
}

function PrepButton({
  applicationId,
  action,
  label,
}: {
  applicationId: number;
  action: (formData: FormData) => Promise<void>;
  label: string;
}) {
  return (
    <form action={action}>
      <input type="hidden" name="application_id" value={applicationId} />
      <Button type="submit" size="sm" className="h-7 px-2 text-[11px]">
        {label}
      </Button>
    </form>
  );
}

function ApplicationArtifacts({ application }: { application: ApplicationRecord }) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-950">
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-slate-50">Artifacts</div>
          <div className="mt-1 text-xs text-slate-500">Tailored CV, prep notes, and application drafts.</div>
        </div>
        <form action={generateApplicationArtifactsAction}>
          <input type="hidden" name="application_id" value={application.id} />
          <Button type="submit" size="sm" className="h-7 px-2 text-[11px]">
            Generate
          </Button>
        </form>
      </div>
      {application.artifacts.length === 0 ? (
        <div className="px-4 py-4 text-xs text-slate-500">No artifacts yet.</div>
      ) : (
        <div className="divide-y divide-slate-800">
          {application.artifacts.map((artifact) => (
            <ArtifactPreview key={artifact.id} artifact={artifact} />
          ))}
        </div>
      )}
    </section>
  );
}

function ArtifactPreview({ artifact }: { artifact: ApplicationArtifact }) {
  return (
    <div className="px-4 py-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-xs font-semibold text-slate-100">{artifact.title}</div>
          <div className="mt-1 font-mono text-[11px] text-slate-600">{labelize(artifact.artifact_type)} - {artifact.status}</div>
        </div>
        <div className="flex shrink-0 gap-1">
          <ArtifactStatusButton artifactId={artifact.id} status="approved" label="Approve" />
          <ArtifactStatusButton artifactId={artifact.id} status="rejected" label="Reject" />
        </div>
      </div>
      <p className="mt-2 line-clamp-4 whitespace-pre-line text-xs leading-5 text-slate-500">
        {artifact.content}
      </p>
    </div>
  );
}

function ArtifactStatusButton({
  artifactId,
  status,
  label,
}: {
  artifactId: number;
  status: "approved" | "rejected";
  label: string;
}) {
  return (
    <form action={setApplicationArtifactStatusAction}>
      <input type="hidden" name="artifact_id" value={artifactId} />
      <input type="hidden" name="status" value={status} />
      <Button type="submit" size="sm" className="h-7 px-2 text-[11px]">
        {label}
      </Button>
    </form>
  );
}

function statusTone(status: string) {
  switch (status) {
    case "saved":
      return "info" as const;
    case "applied":
    case "interviewing":
    case "offer":
      return "success" as const;
    case "rejected":
    case "withdrawn":
    case "skipped":
      return "neutral" as const;
    default:
      return "warning" as const;
  }
}

function dateInputValue(value: string | null) {
  return value ? value.slice(0, 10) : "";
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "not recorded";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
  }).format(new Date(value));
}

function labelize(value: string) {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

function getSearchParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}
