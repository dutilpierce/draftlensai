/** Payload accepted by `POST /api/feedback` — safe to extend when wiring CRM or email. */
export type FeedbackSubmission = {
  /** Desired feature or outcome */
  featureRequest: string;
  /** e.g. contracts, policy memos, journal submissions */
  workflowType: string;
  /** Friction, confusion, or gap */
  painPoint: string;
  /** Optional — only if the submitter wants a follow-up */
  email?: string;
};
