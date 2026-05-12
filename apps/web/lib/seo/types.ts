import type { Metadata } from "next";

export type SchemaProfile = "home" | "software" | "article" | "standard";

export interface BreadcrumbItem {
  name: string;
  href: string;
}

export interface RelatedLink {
  href: string;
  label: string;
}

/** Typed, auditable definition for every indexable public route. */
export interface RegisteredPage {
  path: string;
  title: string;
  description: string;
  h1: string;
  /** Path only, e.g. /product — used for canonical (clean, no query). */
  canonicalPath: string;
  breadcrumb: BreadcrumbItem[];
  related: RelatedLink[];
  schemaProfile: SchemaProfile;
  /** ISO date string when the on-page “last updated” is truthful. */
  lastModified?: string;
  /** For internal docs / content ops — not rendered as a meta keywords tag. */
  primaryTopic: string;
  secondaryTopics: string[];
}

export type PageMetadataInput = Pick<
  RegisteredPage,
  "title" | "description" | "canonicalPath" | "lastModified"
>;

export type BuiltMarketingMetadata = Metadata;
