import Link from "next/link";
import { IntroBlock, LinkRow, ProseColumn, SectionHeading, SectionShell } from "@/components/marketing/MarketingUi";

const LEGAL_NOTE = (
  <p className="text-sm text-ink-600">
    <strong>Important:</strong> These pages summarize how DraftLens is intended to work and how we think about data
    handling. They are <strong>not</strong> a substitute for legal advice. Have qualified counsel review them before
    you rely on them for compliance, customer contracts, or regulatory filings.
  </p>
);

export function PrivacyPolicyBody() {
  return (
    <>
      <IntroBlock kicker="Summary">{LEGAL_NOTE}</IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Overview">What DraftLens is</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens is an <strong>AI-assisted document review, proofreading, and fix</strong> platform. You upload
            manuscripts (for example <strong>PDF</strong> or <strong>Microsoft Word</strong> files), optionally add
            supporting or context files, and receive structured outputs such as issue lists, summaries, reviewed or
            corrected documents, and related logs. DraftLens is <strong>not</strong> a law firm and does{" "}
            <strong>not</strong> provide legal, financial, medical, tax, or other professional advice.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="Collection">Information we may collect</SectionHeading>
        <ProseColumn>
          <ul>
            <li>
              <strong>Account and session information</strong> — for example the email address you use to start a
              session in the app.
            </li>
            <li>
              <strong>Main documents</strong> you upload for review or fix.
            </li>
            <li>
              <strong>Supporting, source, or context files</strong> you attach when your plan allows it.
            </li>
            <li>
              <strong>Text and instructions you type</strong> into the product (for example context, review focus, or
              do-not-change notes).
            </li>
            <li>
              <strong>Generated outputs</strong> from review or fix runs (documents, PDFs, reports, ledgers, logs, and
              similar artifacts).
            </li>
            <li>
              <strong>Feedback</strong> you submit through feedback or feature-request flows, including optional
              attachments you choose to include.
            </li>
            <li>
              <strong>Google Drive</strong> — if you connect or use Drive, we process the files and metadata involved in
              the import or save-back actions you initiate (for example file identifiers, names, and content needed to
              run the job).
            </li>
            <li>
              <strong>Payment and subscription data</strong> processed by <strong>Stripe</strong> (such as plan status
              and billing events). DraftLens does not need to store full payment card numbers to operate hosted Checkout;
              card details are handled by Stripe according to its terms and privacy policy.
            </li>
            <li>
              <strong>Operational data</strong> such as job identifiers, status, errors, timestamps, and security or
              diagnostic logs needed to run and protect the service.
            </li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Use">How we use information</SectionHeading>
        <ProseColumn>
          <ul>
            <li>To provide document review, proofreading, fix, and export features you request.</li>
            <li>To generate reviewed or corrected outputs and related artifacts.</li>
            <li>To process supporting or context files you provide.</li>
            <li>To manage subscriptions, entitlements, and fair-use limits.</li>
            <li>To troubleshoot, secure, maintain, and improve the product.</li>
            <li>To respond to support or feedback messages you send us.</li>
            <li>To perform Google Drive import or save-back when you choose those actions.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Models">AI and model providers</SectionHeading>
        <ProseColumn>
          <p>
            To perform review and fix workflows, DraftLens may send <strong>document text or extracted content</strong>
            , together with instructions and context you supply, to <strong>third-party AI model providers</strong>.
            Depending on how your deployment is configured, those providers may include{" "}
            <strong>OpenAI</strong>, <strong>Anthropic</strong>, <strong>Google (Gemini)</strong>, or other model
            vendors added over time. Those companies process data under their own terms and privacy policies.
          </p>
          <p>
            You should <strong>not upload content</strong> you are not authorized to share with such providers. You are
            responsible for verifying outputs before you rely on them for filing, publication, or decisions.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="sage">
        <SectionHeading eyebrow="Drive">Google Drive</SectionHeading>
        <ProseColumn>
          <p>
            If you use Google Drive integration, DraftLens accesses Drive <strong>only in connection with actions you</strong>{" "}
            take—such as choosing a file to import or asking us to save a new output file. We do{" "}
            <strong>not</strong> claim to manage, scan, or synchronize your entire Drive. Save-back creates{" "}
            <strong>new files</strong>; we do not silently overwrite your originals in Google Docs or other native formats
            in place. Google&apos;s own terms and security practices also apply.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Retention">Retention and deletion</SectionHeading>
        <ProseColumn>
          <p>
            Uploaded files and generated outputs are kept <strong>only as long as needed</strong> to operate the service
            and according to <strong>retention settings configured for your deployment</strong>. Jobs are typically
            assigned a scheduled deletion time (for example based on a default hour window, or a{" "}
            <strong>shorter window</strong> when you enable sensitive-style handling for a run). A background process
            removes eligible files after that time; <strong>exact timing can vary</strong> with load and maintenance, so
            we do not promise immediate deletion the moment a job completes.
          </p>
          <p>
            Some <strong>metadata or logs</strong> may be retained longer for security, troubleshooting, billing, or legal
            reasons, or where the product still depends on them.
          </p>
          <p>
            There is <strong>no self-service “delete everything” button</strong> guaranteed in the product today. For
            deletion requests, contact us at{" "}
            <a href="mailto:privacy@draftlensai.com">privacy@draftlensai.com</a> (see also{" "}
            <Link href="/data-security">Data security</Link>). We will respond consistent with our capabilities and
            applicable law.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="blush">
        <SectionHeading eyebrow="Sharing">Service providers and disclosure</SectionHeading>
        <ProseColumn>
          <p>We use subprocessors and infrastructure partners as needed to run DraftLens, which may include:</p>
          <ul>
            <li>AI model providers (as described above).</li>
            <li>Cloud hosting and storage vendors.</li>
            <li>Payment processing (Stripe).</li>
            <li>Email or analytics vendors if you enable them for a deployment.</li>
          </ul>
          <p>
            We may also access, preserve, or disclose information if we reasonably believe it is necessary to comply with
            law, protect safety, or enforce our terms.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Security">Security</SectionHeading>
        <ProseColumn>
          <p>
            We use reasonable administrative, technical, and organizational measures appropriate to the service. No
            method of transmission or storage is perfectly secure. You should use strong access practices and avoid
            uploading materials you are not permitted to process.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Children">Children</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens is <strong>not intended for children under 13</strong> or for minors where prohibited. Do not use
            the service if you are not old enough to consent in your jurisdiction.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="International">International users</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens may be operated from or hosted in the United States or other regions. If you use the service from
            outside those regions, your information may be processed where we or our providers operate. We do{" "}
            <strong>not</strong> represent that the product satisfies every local law; consult counsel if you have
            cross-border requirements.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Changes">Changes to this policy</SectionHeading>
        <ProseColumn>
          <p>
            We may update this policy from time to time. Material changes will be reflected by updating this page and
            the “Last updated” date shown in the page header.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Contact">Contact</SectionHeading>
        <ProseColumn>
          <p>
            Privacy questions: <a href="mailto:privacy@draftlensai.com">privacy@draftlensai.com</a>
            <br />
            General support: <a href="mailto:support@draftlensai.com">support@draftlensai.com</a>
          </p>
          <p className="text-sm text-ink-500">
            Before listing these addresses in Google OAuth branding or customer materials, configure mailboxes or
            forwarding—see <code className="rounded bg-ink-100 px-1">docs/trust-and-email-setup.md</code>.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <LinkRow
          links={[
            { href: "/terms", label: "Terms of Service" },
            { href: "/data-security", label: "Data security" },
            { href: "/contact", label: "Contact" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function TermsOfServiceBody() {
  return (
    <>
      <IntroBlock kicker="Summary">{LEGAL_NOTE}</IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Agreement">Acceptance</SectionHeading>
        <ProseColumn>
          <p>
            By accessing or using DraftLens (including the marketing site and the in-browser app), you agree to these
            Terms and to our <Link href="/privacy">Privacy Policy</Link>. If you do not agree, do not use the service.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="Service">What DraftLens provides</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens provides <strong>AI-assisted</strong> document review, proofreading, redline-style analysis, and—
            where your plan and settings allow—<strong>corrected document generation</strong>, summaries, issue lists,
            and related outputs. Features may change; descriptions on the site or in the app are not a warranty of
            future availability.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Advice">No professional advice</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens is <strong>not a law firm</strong> and does <strong>not</strong> provide legal, financial,
            medical, tax, or other professional advice. AI-generated content may be incomplete, inaccurate, biased, or
            unsuitable for your situation. <strong>You</strong> are responsible for review, judgment, and final use of all
            outputs. Where stakes are high, consult a qualified professional.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Your responsibilities">Your responsibilities</SectionHeading>
        <ProseColumn>
          <ul>
            <li>You represent that you have the rights and authority needed to upload and process your documents.</li>
            <li>You will not upload unlawful content or use DraftLens to violate others&apos; rights.</li>
            <li>You will verify outputs before filing, publishing, or relying on them.</li>
            <li>You will not attempt to abuse, overload, scrape, reverse engineer, or circumvent usage limits or billing.</li>
            <li>You will not upload malware or content designed to harm the service or others.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="sage">
        <SectionHeading eyebrow="License to us">Your content and our license to operate</SectionHeading>
        <ProseColumn>
          <p>
            You retain ownership of your documents. You grant DraftLens and its subprocessors a{" "}
            <strong>limited license</strong> to host, process, transmit, display, and create derivative outputs solely to
            provide the service you request—including sending content to AI and cloud providers as described in the{" "}
            <Link href="/privacy">Privacy Policy</Link> and <Link href="/data-security">Data security</Link> pages.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Cloud">Google Drive and other integrations</SectionHeading>
        <ProseColumn>
          <p>
            Optional integrations (such as Google Drive, Dropbox, or Microsoft OneDrive) work when{" "}
            <strong>you</strong> choose to connect or select files. Those providers impose their own terms. DraftLens may
            import selected files and save new outputs when you direct it to.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="blush">
        <SectionHeading eyebrow="Billing">Subscriptions and payment</SectionHeading>
        <ProseColumn>
          <p>
            Some features may be limited on free plans and expanded on paid plans. Payments and subscriptions may be
            processed by <strong>Stripe</strong>. Pricing, entitlements, and plan names may change; when they do, we will
            rely on the billing portal and in-product notices where available.{" "}
            <strong>Refund and cancellation rules</strong> follow Stripe and the terms presented at purchase unless we
            publish a different written policy for your account.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Acceptable use">Acceptable use</SectionHeading>
        <ProseColumn>
          <p>In addition to the rules above, you agree not to:</p>
          <ul>
            <li>Use DraftLens in violation of applicable law or third-party platform rules.</li>
            <li>Misrepresent outputs as human-written or guaranteed correct when they are not.</li>
            <li>Probe or attack our systems, or interfere with other users.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="AI limits">AI limitations</SectionHeading>
        <ProseColumn>
          <p>
            Outputs can contain errors. Formatting, layout, citations, and cross-references may not match your original
            perfectly—especially for PDF or long documents. Fix mode on PDF may produce Word-oriented outputs rather than
            a pixel-perfect edited PDF. Always verify the final file you intend to file or publish.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Availability">Availability and changes</SectionHeading>
        <ProseColumn>
          <p>
            We strive for reliable operation but do not guarantee uninterrupted access. We may modify, suspend, or
            discontinue features with or without notice where permitted by law.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Warranties">Disclaimer of warranties</SectionHeading>
        <ProseColumn>
          <p>
            The service is provided <strong>as is</strong> and <strong>as available</strong>. To the maximum extent
            permitted by law, we disclaim implied warranties such as merchantability, fitness for a particular purpose, and
            non-infringement.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Liability">Limitation of liability</SectionHeading>
        <ProseColumn>
          <p>
            To the maximum extent permitted by law, DraftLens and its suppliers will not be liable for indirect,
            incidental, special, consequential, or punitive damages, or for lost profits, data, or goodwill, arising from
            your use of the service. Our aggregate liability for claims relating to the service will not exceed the
            greater of (a) the amounts you paid us for the service in the twelve months before the claim or (b) one
            hundred U.S. dollars (US$100), except where prohibited by law.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="sage">
        <SectionHeading eyebrow="Termination">Suspension</SectionHeading>
        <ProseColumn>
          <p>
            We may suspend or terminate access if we reasonably believe you violated these Terms, created risk, or must
            comply with law.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Updates">Changes to these terms</SectionHeading>
        <ProseColumn>
          <p>
            We may update these Terms. Continued use after the updated “Last updated” date constitutes acceptance of the
            revised Terms to the extent allowed by law.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="blush">
        <SectionHeading eyebrow="Contact">Contact</SectionHeading>
        <ProseColumn>
          <p>
            <a href="mailto:support@draftlensai.com">support@draftlensai.com</a>
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <LinkRow
          links={[
            { href: "/privacy", label: "Privacy Policy" },
            { href: "/data-security", label: "Data security" },
            { href: "/contact", label: "Contact" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function DataSecurityBody() {
  return (
    <>
      <IntroBlock kicker="How to read this page">
        <p>
          This page explains, in plain language, how DraftLens handles documents and AI processing. It is meant to
          support informed decisions—not to replace a full security review, vendor questionnaire, or legal analysis.
        </p>
        {LEGAL_NOTE}
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Uploads">How DraftLens handles uploaded documents</SectionHeading>
        <ProseColumn>
          <p>
            When you run a job, your main manuscript (typically <strong>PDF</strong> or <strong>DOCX</strong>) and any
            permitted supporting files are ingested into a controlled processing pipeline on infrastructure we operate or
            lease. Files are used to execute the review or fix workflow you selected and to produce the outputs listed in
            the app (for example reviewed documents, corrected Word files, PDFs, ledgers, and logs).
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="Pipeline">What happens during review</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens extracts or prepares text from your documents, combines it with the instructions and context you
            provide, and sends relevant content through one or more automated review stages. Those stages may include
            multiple independent model passes, merge logic, and—when configured—additional convergence or arbitration
            steps. The goal is structured, inspectable output—not a single opaque chat response.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Providers">AI provider processing</SectionHeading>
        <ProseColumn>
          <p>
            Document content and related prompts may be transmitted to <strong>third-party AI providers</strong> (for
            example OpenAI, Anthropic, or Google/Gemini, depending on configuration). Those vendors process data on their
            own systems under their own policies. DraftLens does <strong>not</strong> claim that your data stays only on
            DraftLens-owned servers during model inference.
          </p>
          <p>
            Do not upload information you are not authorized to send to such providers. Classified, highly regulated, or
            extremely sensitive material may require a separate enterprise arrangement—this public product may not be
            appropriate without additional controls.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="sage">
        <SectionHeading eyebrow="Drive">Google Drive import and save-back</SectionHeading>
        <ProseColumn>
          <p>
            If enabled for your deployment, you can pick files from Google Drive and optionally save new outputs back to
            Drive. DraftLens requests <strong>limited</strong> permissions consistent with those flows. We import only the
            files you select (or explicitly authorize through the provider UI) and create <strong>new</strong> files when
            you ask to save results—we do not market a full “Drive management” product and do not silently rewrite your
            cloud originals in place.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Retention">Retention and deletion (overview)</SectionHeading>
        <ProseColumn>
          <p>
            Completed jobs receive a <strong>scheduled deletion time</strong> based on deployment settings—commonly a
            default hour-based window, with a <strong>shorter</strong> window when you mark a run as more sensitive in the
            product. A background retention process removes eligible files from our storage after that time. Actual
            deletion can be delayed slightly by operational factors; the in-app notice for a job summarizes intent for
            that run when available.
          </p>
          <p>
            Some operational metadata may persist for billing, abuse prevention, or debugging. Request assistance at{" "}
            <a href="mailto:privacy@draftlensai.com">privacy@draftlensai.com</a> for privacy-related requests.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="blush">
        <SectionHeading eyebrow="Sensitive">Sensitive documents</SectionHeading>
        <ProseColumn>
          <p>
            If your deployment offers a sensitive or shorter-retention mode for a job, use it when appropriate. No
            configuration eliminates all risk: you remain responsible for classification, access control, and whether AI
            review is appropriate at all.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Verification">What you should verify</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Facts, numbers, dates, citations, and quotations.</li>
            <li>Legal, financial, or medical implications with qualified professionals.</li>
            <li>Final formatting and track-changes behavior in Word or PDF tools you rely on.</li>
            <li>That outputs you download or save to cloud storage go only to destinations you trust.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="Limits">Current limitations</SectionHeading>
        <ProseColumn>
          <ul>
            <li>DraftLens is not HIPAA-, SOC 2-, GDPR-, or CCPA-certified as a labeled offering unless we publish separate attestation for your deployment.</li>
            <li>We do not warrant that the service meets any particular regulatory regime without a written agreement.</li>
            <li>Security measures are reasonable for a software-as-a-service product—not a substitute for your own controls.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Contact">Contact</SectionHeading>
        <ProseColumn>
          <p>
            Security reports: <a href="mailto:security@draftlensai.com">security@draftlensai.com</a>
            <br />
            Privacy: <a href="mailto:privacy@draftlensai.com">privacy@draftlensai.com</a>
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <LinkRow
          links={[
            { href: "/privacy", label: "Privacy Policy" },
            { href: "/terms", label: "Terms of Service" },
            { href: "/contact", label: "Contact" },
          ]}
        />
      </SectionShell>
    </>
  );
}
