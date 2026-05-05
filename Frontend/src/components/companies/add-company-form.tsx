import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/form-controls";
import { PageSection } from "@/components/ui/page-section";

type AddCompanyFormProps = {
  action: (formData: FormData) => Promise<void>;
};

export function AddCompanyForm({ action }: AddCompanyFormProps) {
  return (
    <PageSection
      title="Add company"
      description="Add a company by name/domain and let source discovery find the jobs page, or paste a known careers URL."
    >
      <form
        action={action}
        className="grid gap-3 px-4 py-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.4fr)_150px_auto] sm:items-end"
      >
        <label className="min-w-0">
          <span className="text-xs font-medium text-[var(--muted)]">Company name</span>
          <Input
            name="name"
            type="text"
            placeholder="Optional"
          />
        </label>

        <label className="min-w-0">
          <span className="text-xs font-medium text-[var(--muted)]">Domain</span>
          <Input
            name="domain"
            type="text"
            placeholder="example.com"
          />
        </label>

        <label className="min-w-0">
          <span className="text-xs font-medium text-[var(--muted)]">Careers URL</span>
          <Input
            name="careers_url"
            type="url"
            placeholder="https://jobs.lever.co/example"
          />
        </label>

        <label className="min-w-0">
          <span className="text-xs font-medium text-[var(--muted)]">Priority</span>
          <Select
            name="priority_tier"
            defaultValue="normal"
          >
            <option value="dream">Dream</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="fallback">Fallback</option>
          </Select>
        </label>

        <Button type="submit" variant="primary" className="px-4">
          Add
        </Button>
      </form>
    </PageSection>
  );
}
