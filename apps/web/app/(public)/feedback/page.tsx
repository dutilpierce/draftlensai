import { FeedbackPageBody } from "@/components/marketing/feedback-page-body";
import { PublicPageShell } from "@/components/marketing/PublicPageShell";
import { publicMetadata } from "@/lib/seo/metadata-factory";
import { PAGE_REGISTRY } from "@/lib/seo/registry";

const page = PAGE_REGISTRY["/feedback"]!;
export const metadata = publicMetadata(page);

export default function FeedbackPage() {
  return (
    <PublicPageShell page={page}>
      <FeedbackPageBody />
    </PublicPageShell>
  );
}
