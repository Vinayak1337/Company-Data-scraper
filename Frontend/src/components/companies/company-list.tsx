import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Company } from "@/lib/api";
import {
  formatDateTime,
  formatRelativeScan,
  formatSourceType,
  formatWorkMode,
  getCompanyKeywordInputValue,
  getCompanyPriority,
  getCompanyWorkModeFilter,
  getScrapeStatusBadge,
} from "./company-utils";

type CompanyListProps = {
  companies: Company[];
  scrapeAction: (formData: FormData) => Promise<void>;
  updateAction: (formData: FormData) => Promise<void>;
  togglePausedAction: (formData: FormData) => Promise<void>;
  deleteAction: (formData: FormData) => Promise<void>;
  intelligenceAction: (formData: FormData) => Promise<void>;
};

const inputClass =
  "mt-1 h-8 w-full rounded-md border border-slate-300 bg-white px-2 text-xs text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-slate-500 focus:ring-2 focus:ring-slate-200";
const selectClass =
  "mt-1 h-8 w-full rounded-md border border-slate-300 bg-white px-2 text-xs text-slate-950 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200";
const secondaryButtonClass =
  "h-8 rounded-md border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-200";

export function CompanyList({
  companies,
  scrapeAction,
  updateAction,
  togglePausedAction,
  deleteAction,
  intelligenceAction,
}: CompanyListProps) {
  if (companies.length === 0) {
    return (
      <EmptyState
        title="No tracked companies yet"
        message="Add a careers URL to start monitoring jobs and source health."
      />
    );
  }

  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">
          Tracked companies
        </h2>
        <div className="text-xs text-slate-500">{companies.length} total</div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1280px] divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th scope="col" className="px-4 py-3">
                Company
              </th>
              <th scope="col" className="px-4 py-3">
                Source health
              </th>
              <th scope="col" className="px-4 py-3">
                Priority
              </th>
              <th scope="col" className="px-4 py-3">
                Active
              </th>
              <th scope="col" className="px-4 py-3">
                Last scan
              </th>
              <th scope="col" className="px-4 py-3">
                Metadata
              </th>
              <th scope="col" className="px-4 py-3 text-right">
                Controls
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {companies.map((company) => {
              const sourceHealth = getScrapeStatusBadge(company);
              const priority = getCompanyPriority(company);

              return (
                <tr key={company.id} className="align-top hover:bg-slate-50/70">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-950">{company.name}</div>
                    <a
                      href={company.careers_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 block max-w-80 truncate text-xs text-cyan-700 hover:text-cyan-900"
                    >
                      {company.careers_url}
                    </a>
                    <details className="mt-3 rounded-md border border-slate-200 bg-white">
                      <summary className="cursor-pointer px-2 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                        Edit company and filters
                      </summary>
                      <form
                        action={updateAction}
                        className="grid gap-2 border-t border-slate-200 p-2 sm:grid-cols-2 xl:grid-cols-3"
                      >
                        <input
                          type="hidden"
                          name="company_id"
                          value={company.id}
                        />
                        <label className="min-w-0">
                          <span className="text-[11px] font-medium text-slate-600">
                            Name
                          </span>
                          <input
                            name="name"
                            defaultValue={company.name}
                            className={inputClass}
                          />
                        </label>
                        <label className="min-w-0">
                          <span className="text-[11px] font-medium text-slate-600">
                            Priority
                          </span>
                          <select
                            name="priority_tier"
                            defaultValue={
                              company.priority_tier || company.priority || "normal"
                            }
                            className={selectClass}
                          >
                            <option value="dream">Dream</option>
                            <option value="high">High</option>
                            <option value="normal">Normal</option>
                            <option value="fallback">Fallback</option>
                          </select>
                        </label>
                        <label className="min-w-0">
                          <span className="text-[11px] font-medium text-slate-600">
                            Work mode
                          </span>
                          <select
                            name="work_mode_filter"
                            defaultValue={getCompanyWorkModeFilter(company)}
                            className={selectClass}
                          >
                            <option value="">Any</option>
                            <option value="remote">Remote</option>
                            <option value="hybrid">Hybrid</option>
                            <option value="onsite">Onsite</option>
                          </select>
                        </label>
                        <label className="min-w-0">
                          <span className="text-[11px] font-medium text-slate-600">
                            Title keywords
                          </span>
                          <input
                            name="title_keywords"
                            defaultValue={getCompanyKeywordInputValue(
                              company,
                              "title_keywords",
                            )}
                            placeholder="engineer, backend"
                            className={inputClass}
                          />
                        </label>
                        <label className="min-w-0">
                          <span className="text-[11px] font-medium text-slate-600">
                            Negative title keywords
                          </span>
                          <input
                            name="negative_title_keywords"
                            defaultValue={getCompanyKeywordInputValue(
                              company,
                              "negative_title_keywords",
                            )}
                            placeholder="intern, manager"
                            className={inputClass}
                          />
                        </label>
                        <label className="min-w-0">
                          <span className="text-[11px] font-medium text-slate-600">
                            Location keywords
                          </span>
                          <input
                            name="location_keywords"
                            defaultValue={getCompanyKeywordInputValue(
                              company,
                              "location_keywords",
                            )}
                            placeholder="India, Remote"
                            className={inputClass}
                          />
                        </label>
                        <label className="min-w-0">
                          <span className="text-[11px] font-medium text-slate-600">
                            Scan every hours
                          </span>
                          <input
                            name="scan_frequency_hours"
                            type="number"
                            min="1"
                            max="720"
                            defaultValue={company.scan_frequency_hours || 24}
                            className={inputClass}
                          />
                        </label>
                        <label className="flex min-w-0 items-center gap-2 pt-5 text-xs font-medium text-slate-700">
                          <input
                            name="alert_new_roles"
                            type="checkbox"
                            defaultChecked={company.alert_new_roles}
                            className="h-4 w-4 rounded border-slate-300 text-slate-950 focus:ring-slate-300"
                          />
                          New-role alerts
                        </label>
                        <div className="flex items-center justify-end sm:col-span-2 xl:col-span-3">
                          <button
                            type="submit"
                            className="h-8 rounded-md bg-slate-950 px-3 text-xs font-semibold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300"
                          >
                            Save changes
                          </button>
                        </div>
                      </form>
                    </details>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1.5">
                      <StatusBadge tone={sourceHealth.tone} withDot>
                        {sourceHealth.label}
                      </StatusBadge>
                      <span className="text-xs text-slate-500">
                        {formatSourceType(company.scraper_type)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge tone={priority.tone}>{priority.label}</StatusBadge>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge
                      tone={company.is_active ? "success" : "neutral"}
                      withDot
                    >
                      {company.is_active ? "Active" : "Paused"}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-800">
                      {formatDateTime(company.last_scraped_at)}
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      {formatRelativeScan(company.last_scraped_at)}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="max-w-72 text-xs leading-5 text-slate-600">
                      <div>
                        {company.last_scrape_message ||
                          "No scan message recorded."}
                      </div>
                      <div className="mt-1 text-slate-500">
                        Failures: {company.consecutive_failure_count}
                      </div>
                      <div className="text-slate-500">
                        New role: {formatDateTime(company.last_new_role_at)}
                      </div>
                      <div className="text-slate-500">
                        Work mode: {formatWorkMode(getCompanyWorkModeFilter(company))}
                      </div>
                      <div className="text-slate-500">
                        Cadence: every {company.scan_frequency_hours || 24}h
                      </div>
                      <div className="text-slate-500">
                        Alerts: {company.alert_new_roles ? "New roles" : "Off"}
                      </div>
                      <div className="mt-2 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-slate-600">
                        <div className="font-semibold text-slate-700">Intelligence</div>
                        <div className="mt-1">
                          {company.latest_intelligence?.summary || "No company intelligence generated."}
                        </div>
                        {company.latest_intelligence?.risk_flags?.length ? (
                          <div className="mt-1 text-amber-700">
                            Risks: {company.latest_intelligence.risk_flags.length}
                          </div>
                        ) : null}
                        <div className="mt-1 text-slate-500">
                          Contacts: {company.recruiter_contacts_count || 0}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex min-w-48 flex-col items-end gap-2">
                      <div className="flex justify-end gap-2">
                        <form action={scrapeAction}>
                          <input
                            type="hidden"
                            name="company_id"
                            value={company.id}
                          />
                          <button type="submit" className={secondaryButtonClass}>
                            Scan
                          </button>
                        </form>
                        <form action={intelligenceAction}>
                          <input
                            type="hidden"
                            name="company_id"
                            value={company.id}
                          />
                          <button type="submit" className={secondaryButtonClass}>
                            Intel
                          </button>
                        </form>
                        <form action={togglePausedAction}>
                          <input
                            type="hidden"
                            name="company_id"
                            value={company.id}
                          />
                          <input
                            type="hidden"
                            name="operation"
                            value={company.is_active ? "pause" : "resume"}
                          />
                          <button type="submit" className={secondaryButtonClass}>
                            {company.is_active ? "Pause" : "Resume"}
                          </button>
                        </form>
                      </div>
                      <form
                        action={deleteAction}
                        className="w-48 rounded-md border border-rose-200 bg-rose-50/70 p-2 text-left"
                      >
                        <input
                          type="hidden"
                          name="company_id"
                          value={company.id}
                        />
                        <label className="block">
                          <span className="text-[11px] font-semibold text-rose-800">
                            Delete company
                          </span>
                          <input
                            name="delete_confirm"
                            placeholder="Type DELETE"
                            className="mt-1 h-7 w-full rounded-md border border-rose-200 bg-white px-2 text-xs text-rose-950 outline-none placeholder:text-rose-300 focus:border-rose-400 focus:ring-2 focus:ring-rose-100"
                          />
                        </label>
                        <button
                          type="submit"
                          className="mt-2 h-7 w-full rounded-md border border-rose-300 bg-white px-2 text-xs font-semibold text-rose-700 transition hover:border-rose-400 hover:bg-rose-100 focus:outline-none focus:ring-2 focus:ring-rose-100"
                        >
                          Delete
                        </button>
                      </form>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
