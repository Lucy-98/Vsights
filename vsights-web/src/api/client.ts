// Client gọi vsights-api theo ràng buộc ở base/03 mục 10 và base/02 mục 5:
// - access token chỉ giữ trong bộ nhớ (biến module), không ghi localStorage;
// - refresh token nằm trong cookie HttpOnly `vs_refresh` (Path=/auth), trình duyệt tự gửi;
// - gặp 401 thì gọi POST /auth/refresh rồi thử lại yêu cầu đúng một lần;
// - việc làm mới được tuần tự hoá giữa các tab bằng Web Locks API (lỗ hổng L5),
//   vì máy chủ coi một refresh token bị gửi lại là bị đánh cắp và thu hồi cả họ phiên.

export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? 'http://localhost:8000';

/** Lỗi theo đúng dạng `{ma_loi, thong_bao, chi_tiet}` của vsights-api. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly maLoi: string,
    public readonly thongBao: string,
    public readonly chiTiet: unknown = null,
    public readonly retryAfter: number | null = null,
  ) {
    super(thongBao);
  }
}

export interface TokenResponse {
  access_token: string;
  token_type?: string;
  expires_in?: number;
}

let accessToken: string | null = null;
let refreshDangChay: Promise<string | null> | null = null;
const nguoiNghe = new Set<(token: string | null) => void>();

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  nguoiNghe.forEach((fn) => fn(token));
}

/** Đăng ký nhận thông báo khi phiên thay đổi (đăng nhập, làm mới thất bại, đăng xuất). */
export function onTokenChange(fn: (token: string | null) => void): () => void {
  nguoiNghe.add(fn);
  return () => nguoiNghe.delete(fn);
}

async function docLoi(res: Response): Promise<ApiError> {
  let body: { ma_loi?: string; thong_bao?: string; chi_tiet?: unknown; detail?: unknown } = {};
  try {
    body = await res.json();
  } catch {
    /* thân rỗng hoặc không phải JSON */
  }
  const retry = Number(res.headers.get('Retry-After'));
  return new ApiError(
    res.status,
    body.ma_loi ?? `HTTP_${res.status}`,
    body.thong_bao ?? thongBaoMacDinh(res.status),
    body.chi_tiet ?? body.detail ?? null,
    Number.isFinite(retry) && retry > 0 ? retry : null,
  );
}

function thongBaoMacDinh(status: number): string {
  if (status === 0) return 'Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.';
  if (status === 401) return 'Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.';
  if (status === 403) return 'Bạn không có quyền thực hiện thao tác này.';
  if (status === 404) return 'Không tìm thấy dữ liệu.';
  if (status === 429) return 'Bạn thử quá nhiều lần. Vui lòng đợi rồi thử lại.';
  if (status >= 500) return 'Máy chủ đang gặp sự cố. Vui lòng thử lại sau.';
  return 'Yêu cầu không thành công.';
}

async function goiRefresh(): Promise<string | null> {
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: 'POST',
    credentials: 'include', // gửi cookie vs_refresh
  });
  if (!res.ok) {
    setAccessToken(null);
    return null;
  }
  const data = (await res.json()) as TokenResponse;
  setAccessToken(data.access_token);
  return data.access_token;
}

/**
 * Làm mới access token. Trong một tab: gộp các lời gọi đồng thời thành một.
 * Giữa các tab: giữ khoá Web Locks "vs-refresh" để không có hai lần refresh chạy cùng lúc.
 */
export function refreshAccessToken(): Promise<string | null> {
  if (refreshDangChay) return refreshDangChay;
  const chay = async () => {
    try {
      if (typeof navigator !== 'undefined' && navigator.locks?.request) {
        return await navigator.locks.request('vs-refresh', goiRefresh);
      }
      return await goiRefresh();
    } catch {
      setAccessToken(null);
      return null;
    }
  };
  refreshDangChay = chay().finally(() => {
    refreshDangChay = null;
  });
  return refreshDangChay;
}

type GiaTriQuery = string | number | boolean | undefined | null;

export interface ApiOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  /** Không tự làm mới khi gặp 401 (dùng cho chính các endpoint /auth/*). */
  boQuaRefresh?: boolean;
  /** Mảng → lặp lại tham số (`ma_tien_nghi=1&ma_tien_nghi=2`), đúng cách FastAPI đọc `list[int]` (T-027). */
  query?: Record<string, GiaTriQuery | GiaTriQuery[]>;
}

function taoUrl(path: string, query?: ApiOptions['query']): string {
  const url = new URL(`${API_URL}${path}`);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      const ds = Array.isArray(v) ? v : [v];
      for (const x of ds) {
        if (x !== undefined && x !== null && x !== '') url.searchParams.append(k, String(x));
      }
    }
  }
  return url.toString();
}

export async function api<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { body, boQuaRefresh, query, headers, ...rest } = opts;

  const guiYeuCau = async (): Promise<Response> => {
    const h = new Headers(headers);
    h.set('Accept', 'application/json');
    if (body !== undefined) h.set('Content-Type', 'application/json');
    if (accessToken) h.set('Authorization', `Bearer ${accessToken}`);
    try {
      return await fetch(taoUrl(path, query), {
        ...rest,
        headers: h,
        credentials: 'include',
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') throw e; // người gọi tự huỷ
      throw new ApiError(0, 'LOI_MANG', thongBaoMacDinh(0));
    }
  };

  let res = await guiYeuCau();
  if (res.status === 401 && !boQuaRefresh && accessToken) {
    const moi = await refreshAccessToken();
    if (moi) res = await guiYeuCau(); // thử lại đúng một lần
  }
  if (!res.ok) throw await docLoi(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Dạng phân trang chung của vsights-api. */
export interface Trang<T> {
  items: T[];
  tong: number;
  trang: number;
  kich_thuoc: number;
}
