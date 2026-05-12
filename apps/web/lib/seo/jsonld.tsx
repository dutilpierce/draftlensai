import { absoluteUrl, BRAND, brandLogoAbsoluteUrl } from "./site";

export function JsonLd({ data }: { data: Record<string, unknown> | Record<string, unknown>[] }) {
  const json = JSON.stringify(data);
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />;
}

export function organizationJsonLd(): Record<string, unknown> {
  const base = absoluteUrl("/");
  const org: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: BRAND.name,
    url: base,
    description: BRAND.tagline,
    logo: brandLogoAbsoluteUrl(),
  };
  if (BRAND.emailPlaceholder) org.email = BRAND.emailPlaceholder;
  return org;
}

export function websiteJsonLd(): Record<string, unknown> {
  const base = absoluteUrl("/");
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "DraftLens",
    url: base,
    description:
      "Multi-model document review — review mode, fix mode, and optional supporting evidence for DOCX or PDF manuscripts.",
  };
}

export function softwareApplicationJsonLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "DraftLens",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    url: absoluteUrl("/product"),
    offers: {
      "@type": "Offer",
      url: absoluteUrl("/pricing"),
      priceCurrency: "USD",
      description: "Free tier with limits; Pro subscription. See the pricing page for current details.",
    },
  };
}

export function breadcrumbJsonLd(items: { name: string; href: string }[]): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((it, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: it.name,
      item: absoluteUrl(it.href),
    })),
  };
}

export function articleJsonLd(args: {
  headline: string;
  description: string;
  path: string;
  datePublished?: string;
  dateModified?: string;
}): Record<string, unknown> {
  const publisher: Record<string, unknown> = {
    "@type": "Organization",
    name: "DraftLens",
    logo: { "@type": "ImageObject", url: brandLogoAbsoluteUrl() },
  };

  const out: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: args.headline,
    description: args.description,
    url: absoluteUrl(args.path),
    author: {
      "@type": "Organization",
      name: "DraftLens Editorial Team",
    },
    publisher,
  };
  if (args.datePublished) out.datePublished = args.datePublished;
  if (args.dateModified) out.dateModified = args.dateModified;
  return out;
}
