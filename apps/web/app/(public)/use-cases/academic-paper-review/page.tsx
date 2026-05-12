import { UseAcademicBody } from "@/components/marketing/wave1-bodies";
import { PublicPageShell } from "@/components/marketing/PublicPageShell";
import { publicMetadata } from "@/lib/seo/metadata-factory";
import { PAGE_REGISTRY } from "@/lib/seo/registry";

const page = PAGE_REGISTRY["/use-cases/academic-paper-review"]!;
export const metadata = publicMetadata(page);

export default function Page() {
  return (
    <PublicPageShell page={page}>
      <UseAcademicBody />
    </PublicPageShell>
  );
}
