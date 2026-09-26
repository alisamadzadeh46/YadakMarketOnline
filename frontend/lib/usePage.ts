"use client";
// Page number for a filtered, paginated list.
//
// Lists used to reset the page with `useEffect(() => setPage(1), [filter])`.
// That runs *after* the render in which the filter changed, so the data effect
// of that same render still requested the old page number with the new filter.
// When the new result set is shorter, the API answers 404 ("invalid page") and
// the list is fetched twice. Deriving the page from the filters instead resets
// it in the very render the filter changes, so exactly one valid request is made.
import { useCallback, useState } from "react";

export function usePage(filters: readonly unknown[]): [number, (page: number) => void] {
  const key = JSON.stringify(filters);
  const [state, setState] = useState({ key, page: 1 });
  const page = state.key === key ? state.page : 1;
  const setPage = useCallback((next: number) => setState({ key, page: next }), [key]);
  return [page, setPage];
}
