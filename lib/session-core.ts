// セッション Cookie の署名と検証（Web Crypto だけを使う。proxy とサーバー関数とテストの共通部分）

export const SESSION_COOKIE = "pnba_session";
export const SESSION_DAYS = 30;

const enc = new TextEncoder();

function b64url(buf: ArrayBuffer): string {
  return Buffer.from(buf).toString("base64url");
}

/** 署名鍵。PNBA_SESSION_SECRET が無ければパスワードから作る（パスワードを変えると全員ログアウトになる）。 */
export async function sessionKey(password: string, secret = ""): Promise<CryptoKey> {
  const material = secret || `pnba-session|${password}`;
  const raw = await crypto.subtle.digest("SHA-256", enc.encode(material));
  return crypto.subtle.importKey("raw", raw, { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

export async function signSession(key: CryptoKey, now = Date.now()): Promise<string> {
  const exp = Math.floor(now / 1000) + SESSION_DAYS * 24 * 3600;
  const body = `v1.${exp}`;
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(body));
  return `${body}.${b64url(sig)}`;
}

export async function verifySession(key: CryptoKey, token: string | undefined, now = Date.now()): Promise<boolean> {
  if (!token) return false;
  const m = /^v1\.(\d{1,12})\.([A-Za-z0-9_-]{20,})$/.exec(token);
  if (!m) return false;
  if (Number(m[1]) * 1000 < now) return false;
  let sig: Buffer;
  try {
    sig = Buffer.from(m[2], "base64url");
  } catch {
    return false;
  }
  // subtle.verify は一定時間で比較する
  return crypto.subtle.verify("HMAC", key, new Uint8Array(sig), enc.encode(`v1.${m[1]}`));
}

/** パスワードを一定時間で比較する（長さが違っても時間が変わらないようにハッシュ同士で比べる）。 */
export async function passwordMatches(input: string, expected: string): Promise<boolean> {
  if (!expected) return false;
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(input)),
    crypto.subtle.digest("SHA-256", enc.encode(expected)),
  ]);
  const x = new Uint8Array(a);
  const y = new Uint8Array(b);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}
