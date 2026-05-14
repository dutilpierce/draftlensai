import { DataSecurityBody } from "@/components/marketing/legal-bodies";
import { PublicPageShell } from "@/components/marketing/PublicPageShell";
import { publicMetadata } from "@/lib/seo/metadata-factory";
import { PAGE_REGISTRY } from "@/lib/seo/registry";

const page = PAGE_REGISTRY["/data-security"]!;
export const metadata = publicMetadata(page);

export default function Page() {
  return (
    <PublicPageShell page={page} layout="reading">
      <DataSecurityBody />
    </PublicPageShell>
  );
}
