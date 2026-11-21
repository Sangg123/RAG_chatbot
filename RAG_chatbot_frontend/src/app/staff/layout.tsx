"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
    Bot,
    Headset,
    LogOut,
    MessageSquare,
    ShieldCheck,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { logout, refreshAccessToken, syncCurrentUser } from "@/lib/auth";
import { useAuth } from "@/lib/use-auth";
import { getSupportStats } from "@/lib/api";

export default function StaffLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const router = useRouter();
    const { user, authenticated, admin, staff } = useAuth();
    const [waitingCount, setWaitingCount] = useState(0);
    const [authReady, setAuthReady] = useState(false);
    const [authError, setAuthError] = useState("");
    const [accessDeniedRole, setAccessDeniedRole] = useState<string | null>(
        null,
    );

    useEffect(() => {
        let cancelled = false;

        const verifySupportAccess = async () => {
            try {
                if (!authenticated) {
                    const refreshed = await refreshAccessToken();
                    if (!refreshed) {
                        router.replace("/login");
                        return;
                    }
                }

                const currentUser = await syncCurrentUser();
                if (cancelled) return;
                setAuthReady(true);
                if (
                    currentUser.role !== "admin" &&
                    currentUser.role !== "staff"
                ) {
                    setAccessDeniedRole(currentUser.role);
                }
            } catch (error) {
                if (cancelled) return;
                setAuthError(
                    error instanceof Error
                        ? error.message
                        : "Không thể xác minh quyền truy cập.",
                );
                setAuthReady(true);
            }
        };

        void verifySupportAccess();
        return () => {
            cancelled = true;
        };
    }, [authenticated, router]);

    useEffect(() => {
        if (!authenticated || (!admin && !staff)) {
            return;
        }
        let cancelled = false;

        const load = async () => {
            try {
                const stats = await getSupportStats();
                if (!cancelled) setWaitingCount(stats.waiting_count);
            } catch {
                // Header badge is best-effort only.
            }
        };

        void load();
        const interval = window.setInterval(load, 10000);
        return () => {
            cancelled = true;
            window.clearInterval(interval);
        };
    }, [authenticated, admin, staff]);

    if (!authReady || !user) {
        return null;
    }

    if (authError) {
        return (
            <div className="flex h-screen items-center justify-center p-6 text-center">
                <div>
                    <p className="font-semibold text-destructive">
                        Không thể xác minh quyền truy cập bàn hỗ trợ.
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                        {authError}
                    </p>
                </div>
            </div>
        );
    }

    if (accessDeniedRole) {
        return (
            <div className="flex h-screen items-center justify-center p-6 text-center">
                <div>
                    <p className="font-semibold text-destructive">
                        Tài khoản không có quyền truy cập bàn hỗ trợ.
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                        API hiện tại xác nhận {user.username} có role{" "}
                        <strong>{accessDeniedRole}</strong>, cần role staff
                        hoặc admin. Nếu role trong Neon đang là staff, hãy kiểm
                        tra NEXT_PUBLIC_API_URL trên Vercel và DATABASE_URL
                        trên Render có trỏ cùng môi trường không.
                    </p>
                </div>
            </div>
        );
    }

    const handleLogout = () => {
        logout();
        router.push("/login");
    };

    const isActive = (href: string) => pathname === href;

    return (
        <div className="flex h-screen flex-col overflow-hidden bg-background">
            <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-card px-4 sm:px-6">
                <Link href="/staff" className="flex items-center gap-2.5">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm shadow-emerald-600/25">
                        <Headset className="size-5" />
                    </span>
                    <span className="hidden flex-col leading-tight sm:flex">
                        <span className="text-sm font-bold text-foreground">
                            RAG Support
                        </span>
                        <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                            Staff workspace
                        </span>
                    </span>
                </Link>

                <nav className="ml-2 flex items-center gap-1 sm:ml-6">
                    <Link
                        href="/staff"
                        className={cn(
                            "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                            isActive("/staff")
                                ? "bg-emerald-500/10 text-emerald-700"
                                : "text-muted-foreground hover:bg-muted hover:text-foreground",
                        )}
                    >
                        <MessageSquare className="size-4" />
                        <span className="max-sm:hidden">Bàn hỗ trợ</span>
                        {waitingCount > 0 && (
                            <Badge
                                variant="destructive"
                                className="h-5 min-w-5 justify-center rounded-full px-1.5 text-[10px]"
                            >
                                {waitingCount}
                            </Badge>
                        )}
                    </Link>
                    <Link
                        href="/chat?mode=ai"
                        className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                    >
                        <Bot className="size-4" />
                        <span className="max-sm:hidden">Chat với AI</span>
                    </Link>
                </nav>

                <div className="ml-auto flex items-center gap-2 sm:gap-3">
                    <Badge
                        variant="outline"
                        className="hidden items-center gap-1.5 border-emerald-500/20 bg-emerald-500/10 text-emerald-700 sm:flex"
                    >
                        <span className="size-1.5 rounded-full bg-emerald-500" />
                        Đang trực
                    </Badge>
                    <div className="hidden items-center gap-1.5 text-xs text-muted-foreground md:flex">
                        <ShieldCheck className="size-3.5" />
                        {user.role === "admin" ? "Admin" : "Nhân viên"}
                    </div>
                    <div className="flex items-center gap-2">
                        <Avatar className="size-8">
                            <AvatarFallback className="bg-emerald-600 text-xs font-bold text-white">
                                {user.username.charAt(0).toUpperCase()}
                            </AvatarFallback>
                        </Avatar>
                        <span className="hidden max-w-[120px] truncate text-sm font-medium text-foreground sm:block">
                            {user.username}
                        </span>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon-sm"
                        className="text-muted-foreground hover:text-destructive"
                        onClick={handleLogout}
                        aria-label="Đăng xuất"
                    >
                        <LogOut />
                    </Button>
                </div>
            </header>

            <main className="min-h-0 flex-1 overflow-hidden bg-muted/30">
                {children}
            </main>
        </div>
    );
}
