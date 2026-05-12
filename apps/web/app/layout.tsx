import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { getSiteUrl } from "@/lib/seo/site";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const site = getSiteUrl();
const googleVerification = process.env.GOOGLE_SITE_VERIFICATION?.trim();
const gaId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID?.trim();
const gtmId = process.env.NEXT_PUBLIC_GTM_ID?.trim();

export const metadata: Metadata = {
  metadataBase: new URL(site),
  title: { default: "DraftLens", template: "%s · DraftLens" },
  description: "Multi-model document review for Word and PDF — review mode, fix mode, structured findings.",
  applicationName: "DraftLens",
  icons: {
    icon: [{ url: "/brand/draftlens-logo.png", type: "image/png" }],
    apple: [{ url: "/brand/draftlens-logo.png", type: "image/png" }],
  },
  openGraph: { type: "website", siteName: "DraftLens" },
  twitter: { card: "summary_large_image" },
  ...(googleVerification ? { verification: { google: googleVerification } } : {}),
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans`}>
        {gtmId ? (
          <Script id="gtm-base" strategy="afterInteractive">{`
            (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
            new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
            j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
            'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
            })(window,document,'script','dataLayer','${gtmId}');
          `}</Script>
        ) : null}
        {gtmId ? (
          <noscript>
            <iframe
              title="Google Tag Manager"
              src={`https://www.googletagmanager.com/ns.html?id=${gtmId}`}
              height={0}
              width={0}
              style={{ display: "none", visibility: "hidden" }}
            />
          </noscript>
        ) : null}
        {gaId && !gtmId ? (
          <>
            <Script src={`https://www.googletagmanager.com/gtag/js?id=${gaId}`} strategy="afterInteractive" />
            <Script id="ga4-init" strategy="afterInteractive">{`
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());
              gtag('config', '${gaId}');
            `}</Script>
          </>
        ) : null}
        {children}
      </body>
    </html>
  );
}
