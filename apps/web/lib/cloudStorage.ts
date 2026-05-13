/** Browser-side cloud pickers and PKCE helpers. Secrets stay on the API; only public client ids / picker keys are used here. */

const GOOGLE_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file";

export async function loadScript(src: string, id?: string): Promise<void> {
  if (id && document.getElementById(id)) return;
  await new Promise<void>((resolve, reject) => {
    const s = document.createElement("script");
    if (id) s.id = id;
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`script_load_failed:${src}`));
    document.head.appendChild(s);
  });
}

async function sha256Base64Url(input: string): Promise<string> {
  const enc = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", enc);
  const bytes = new Uint8Array(digest);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  const b64 = btoa(bin);
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export async function newPkcePair(): Promise<{ verifier: string; challenge: string }> {
  const arr = new Uint8Array(32);
  crypto.getRandomValues(arr);
  const verifier = btoa(String.fromCharCode(...arr))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
  const challenge = await sha256Base64Url(verifier);
  return { verifier, challenge };
}

export function oauthRedirectUri(): string {
  return `${window.location.origin}/app`;
}

export function startDropboxPkceOAuth(appKey: string): void {
  const state = `dl_oauth_${crypto.randomUUID()}`;
  void newPkcePair().then(({ verifier, challenge }) => {
    sessionStorage.setItem(state, verifier);
    sessionStorage.setItem("dl_oauth_kind", "dropbox");
    const u = new URL("https://www.dropbox.com/oauth2/authorize");
    u.searchParams.set("response_type", "code");
    u.searchParams.set("client_id", appKey);
    u.searchParams.set("redirect_uri", oauthRedirectUri());
    u.searchParams.set("token_access_type", "offline");
    u.searchParams.set("code_challenge", challenge);
    u.searchParams.set("code_challenge_method", "S256");
    u.searchParams.set("state", state);
    window.location.assign(u.toString());
  });
}

export function startMicrosoftPkceOAuth(clientId: string): void {
  const state = `dl_oauth_${crypto.randomUUID()}`;
  void newPkcePair().then(({ verifier, challenge }) => {
    sessionStorage.setItem(state, verifier);
    sessionStorage.setItem("dl_oauth_kind", "microsoft");
    const u = new URL("https://login.microsoftonline.com/common/oauth2/v2.0/authorize");
    u.searchParams.set("client_id", clientId);
    u.searchParams.set("response_type", "code");
    u.searchParams.set("redirect_uri", oauthRedirectUri());
    u.searchParams.set("response_mode", "query");
    u.searchParams.set("scope", "Files.ReadWrite offline_access");
    u.searchParams.set("code_challenge", challenge);
    u.searchParams.set("code_challenge_method", "S256");
    u.searchParams.set("state", state);
    window.location.assign(u.toString());
  });
}

export async function getGoogleAccessToken(clientId: string): Promise<string> {
  await loadScript("https://accounts.google.com/gsi/client", "ggsi");
  const google = (window as unknown as { google?: { accounts?: { oauth2?: { initTokenClient: (x: unknown) => { requestAccessToken: (o?: unknown) => void } } } } }).google;
  const oauth2 = google?.accounts?.oauth2;
  if (!oauth2) throw new Error("google_gis_missing");
  return new Promise((resolve, reject) => {
    const client = oauth2.initTokenClient({
      client_id: clientId,
      scope: GOOGLE_DRIVE_SCOPE,
      callback: (resp: { access_token?: string; error?: string }) => {
        if (resp.error) reject(new Error(resp.error));
        else if (!resp.access_token) reject(new Error("no_access_token"));
        else resolve(resp.access_token);
      },
    });
    client.requestAccessToken({ prompt: "" });
  });
}

export type GoogleDrivePick = { id: string; name: string; mimeType?: string };

export async function pickFromGoogleDrive(args: {
  clientId: string;
  pickerApiKey: string;
}): Promise<{ pick: GoogleDrivePick; accessToken: string }> {
  await loadScript("https://apis.google.com/js/api.js", "gapi");
  const gapiWin = window as unknown as { gapi?: { load: (m: string, cb: () => void) => void } };
  const gapi = gapiWin.gapi;
  if (!gapi) throw new Error("gapi_missing");
  await new Promise<void>((resolve) => gapi.load("picker", () => resolve()));
  const token = await getGoogleAccessToken(args.clientId);
  const win = window as unknown as {
    google?: {
      picker?: {
        PickerBuilder: new () => {
          addView: (v: unknown) => unknown;
          setOAuthToken: (t: string) => unknown;
          setDeveloperKey: (k: string) => unknown;
          setCallback: (cb: (d: unknown) => void) => unknown;
          build: () => { setVisible: (v: boolean) => void };
        };
        DocsView: new (viewId?: unknown) => { setMimeTypes: (m: string) => unknown; setIncludeFolders: (b: boolean) => unknown };
        ViewId: { DOCS: unknown; DOCUMENTS: unknown };
        Action: { PICKED: string; CANCEL: string };
      };
    };
  };
  const google = win.google;
  if (!google?.picker) throw new Error("google_picker_missing");
  const { PickerBuilder, ViewId, Action, DocsView } = google.picker;
  /** PDF, Word, and Google Docs in Drive — matches DraftLens manuscript + evidence formats. */
  const driveMimeFilter =
    "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword,application/vnd.google-apps.document,text/plain,text/markdown";
  const docsView = new DocsView(ViewId.DOCUMENTS).setMimeTypes(driveMimeFilter).setIncludeFolders(false);
  type Chain = { addView: (v: unknown) => Chain; setOAuthToken: (t: string) => Chain; setDeveloperKey: (k: string) => Chain; setCallback: (cb: (d: unknown) => void) => Chain; build: () => { setVisible: (v: boolean) => void } };
  const Builder = PickerBuilder as new () => Chain;
  return new Promise((resolve, reject) => {
    const picker = new Builder()
      .addView(docsView)
      .setOAuthToken(token)
      .setDeveloperKey(args.pickerApiKey)
      .setCallback((data: unknown) => {
        const d = data as { action: string; docs?: { id?: string; name?: string; mimeType?: string }[] };
        if (d.action === Action.PICKED) {
          const doc = d.docs?.[0];
          if (doc?.id) resolve({ pick: { id: doc.id, name: doc.name ?? "document", mimeType: doc.mimeType }, accessToken: token });
          else reject(new Error("picker_empty"));
        } else if (d.action === Action.CANCEL) reject(new Error("cancelled"));
      })
      .build();
    picker.setVisible(true);
  });
}

export function pickFromDropbox(appKey: string): Promise<{ link: string; name: string }> {
  return new Promise((resolve, reject) => {
    const id = "dropboxjs";
    const finish = () => {
      const Dropbox = (window as unknown as { Dropbox?: { choose: (opts: unknown) => void } }).Dropbox;
      if (!Dropbox?.choose) {
        reject(new Error("dropbox_chooser_missing"));
        return;
      }
      Dropbox.choose({
        linkType: "preview",
        multiselect: false,
        extensions: [".pdf", ".docx", ".doc"],
        folderselect: false,
        success: (files: { link: string; name: string }[]) => {
          const f = files?.[0];
          if (!f?.link) reject(new Error("dropbox_empty"));
          else resolve({ link: f.link, name: f.name });
        },
        cancel: () => reject(new Error("cancelled")),
      });
    };
    if (document.getElementById(id)) {
      finish();
      return;
    }
    const s = document.createElement("script");
    s.id = id;
    s.async = true;
    s.src = "https://www.dropbox.com/static/api/2/dropins.js";
    s.setAttribute("data-app-key", appKey);
    s.onload = () => finish();
    s.onerror = () => reject(new Error("script_load_failed:dropins"));
    document.head.appendChild(s);
  });
}

export type OneDrivePick = { id: string; name: string; downloadUrl?: string };

export async function pickFromOneDrive(clientId: string): Promise<OneDrivePick> {
  await loadScript("https://js.live.net/v7.2/OneDrive.js", "odjs");
  const OneDrive = (window as unknown as { OneDrive?: { open: (opts: unknown) => void } }).OneDrive;
  if (!OneDrive?.open) throw new Error("onedrive_js_missing");
  return new Promise((resolve, reject) => {
    OneDrive.open({
      clientId,
      action: "download",
      multiSelect: false,
      advanced: { redirectUri: oauthRedirectUri() },
      success: (r: { value?: { id?: string; name?: string; [k: string]: unknown }[] }) => {
        const v = r?.value?.[0];
        if (!v?.id) reject(new Error("onedrive_empty"));
        else {
          const downloadUrl = typeof v["@microsoft.graph.downloadUrl"] === "string" ? (v["@microsoft.graph.downloadUrl"] as string) : undefined;
          resolve({ id: v.id as string, name: (v.name as string) ?? "document", downloadUrl });
        }
      },
      cancel: () => reject(new Error("cancelled")),
      error: (e: { message?: string } | unknown) =>
        reject(e instanceof Error ? e : new Error(typeof e === "object" && e && "message" in e ? String((e as { message: string }).message) : "onedrive_error")),
    });
  });
}
