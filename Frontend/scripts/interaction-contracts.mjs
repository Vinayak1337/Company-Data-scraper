import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const checks = [
  { route: "Today", files: ["src/app/page.tsx", "src/app/actions.ts"], terms: ["Today", "runDueCrawlsAction", "runAgentAction"] },
  { route: "Companies", files: ["src/app/companies/page.tsx", "src/app/companies/actions.ts"], terms: ["Companies", "listCompanies", "importCompaniesCsvAction", "discoverCompanySourceAction"] },
  { route: "Jobs", files: ["src/app/jobs/page.tsx", "src/app/jobs/actions.ts"], terms: ["Jobs", "listJobs", "submitJobFeedbackAction"] },
  { route: "Profile", files: ["src/app/profile/page.tsx", "src/app/profile/actions.ts"], terms: ["Profile", "getProfile", "importResumeToProfile"] },
  { route: "Settings", files: ["src/app/settings/page.tsx", "src/app/settings/actions.ts"], terms: ["Settings", "updateNotificationPreferencesAction", "updateAgentProviderAction"] },
];

const failures = [];

for (const check of checks) {
  const files = check.files ?? [check.file];
  let source = "";
  for (const file of files) {
    const filePath = join(root, file);
    if (!existsSync(filePath)) {
      failures.push(`${check.route}: missing ${file}`);
      continue;
    }
    source += `\n${readFileSync(filePath, "utf8")}`;
  }
  for (const term of check.terms) {
    if (!source.includes(term)) {
      failures.push(`${check.route}: expected term "${term}" in ${files.join(", ")}`);
    }
  }
}

const shell = readFileSync(join(root, "src/components/shell/app-shell.tsx"), "utf8");
for (const label of ["Today", "Companies", "Jobs", "Profile", "Settings"]) {
  if (!shell.includes(`label: "${label}"`)) {
    failures.push(`App shell: missing nav label ${label}`);
  }
}

if (failures.length) {
  console.error("Frontend interaction contract failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log("Frontend interaction contract passed.");
