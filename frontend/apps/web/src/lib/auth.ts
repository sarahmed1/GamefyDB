import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ApiError, apiFetch } from "./api"

export type User = {
  id: string
  email: string
  is_active: boolean
  is_superuser: boolean
  is_verified: boolean
}

export function useMe() {
  return useQuery<User | null>({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await apiFetch<User>("/api/auth/me")
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) return null
        throw err
      }
    },
    retry: false,
    staleTime: 5 * 60_000,
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (vars: { username: string; password: string }) => {
      await apiFetch<void>("/api/auth/login", {
        method: "POST",
        body: { username: vars.username, password: vars.password },
        contentType: "form",
      })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      await apiFetch<void>("/api/auth/logout", { method: "POST" })
    },
    onSuccess: () => qc.setQueryData(["me"], null),
  })
}
