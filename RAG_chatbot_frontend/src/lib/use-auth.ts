"use client";

import { useSyncExternalStore } from "react";
import { getCurrentUser, isAdmin, isAuthenticated, isStaff } from "@/lib/auth";
import type { User } from "@/lib/api";

type AuthSnapshot = {
  user: User | null;
  authenticated: boolean;
  admin: boolean;
  staff: boolean;
};

const serverSnapshot: AuthSnapshot = {
  user: null,
  authenticated: false,
  admin: false,
  staff: false,
};

let cached: AuthSnapshot = serverSnapshot;

function getSnapshot(): AuthSnapshot {
  const authenticated = isAuthenticated();
  const admin = isAdmin();
  const staff = isStaff();
  const user = getCurrentUser();

  if (
    cached.authenticated !== authenticated ||
    cached.admin !== admin ||
    cached.staff !== staff ||
    cached.user?.id !== user?.id ||
    cached.user?.username !== user?.username ||
    cached.user?.email !== user?.email ||
    cached.user?.role !== user?.role
  ) {
    cached = { user, authenticated, admin, staff };
  }

  return cached;
}

function subscribe(cb: () => void): () => void {
  window.addEventListener("auth-change", cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener("auth-change", cb);
    window.removeEventListener("storage", cb);
  };
}

export function useAuth(): AuthSnapshot {
  return useSyncExternalStore(subscribe, getSnapshot, () => serverSnapshot);
}
