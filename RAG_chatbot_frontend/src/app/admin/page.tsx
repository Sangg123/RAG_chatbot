"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
    Users,
    MessageSquare,
    FileText,
    Star,
    ArrowUpRight,
    RefreshCw,
    LayoutDashboard,
    Database,
} from "lucide-react";
import { getStats, listAllConversations } from "@/lib/api";
import type { Stats, Conversation } from "@/lib/api";
import { cn, formatRelativeTime } from "@/lib/utils";
import {
    Card,
    CardHeader,
    CardTitle,
    CardContent,
    CardAction,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/use-auth";
import dynamic from "next/dynamic";

const DashboardCharts = dynamic(() => import("@/app/admin/dashboard-charts"), {
    ssr: false,
    loading: () => (
        <>
            <div className="grid gap-6 lg:grid-cols-3">
                <Skeleton className="h-72 rounded-xl lg:col-span-2" />
                <Skeleton className="h-72 rounded-xl" />
            </div>
            <Skeleton className="h-56 rounded-xl" />
        </>
    ),
});

export default function AdminDashboard() {
    const [period, setPeriod] = useState("7d");
    const [stats, setStats] = useState<Stats | null>(null);
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [error, setError] = useState<string | null>(null);
    const { user } = useAuth();

    const loadData = async () => {
        setError(null);
        try {
            const [nextStats, nextConversations] = await Promise.all([
                getStats(),
                listAllConversations(),
            ]);
            setStats(nextStats);
            setConversations(nextConversations);
        } catch {
            setError("Không thể kết nối đến server. Hãy kiểm tra backend đang chạy.");
        }
    };

    useEffect(() => {
        void Promise.resolve().then(loadData);
    }, []);

    const statCards = [
        {
            label: "Người dùng",
            value: stats?.total_users ?? "—",
            icon: Users,
            change: "",
        },
        {
            label: "Hội thoại",
            value: stats?.total_conversations?.toLocaleString() ?? "—",
            icon: MessageSquare,
            change: "",
        },
        {
            label: "Tin nhắn",
            value: stats?.total_messages?.toLocaleString() ?? "—",
            icon: Star,
            change: "",
        },
        {
            label: "Tài liệu",
            value: stats?.total_documents ?? "—",
            icon: FileText,
            change: "",
        },
    ];

    const statStyles = [
        "bg-blue-500/10 text-blue-600",
        "bg-violet-500/10 text-violet-600",
        "bg-emerald-500/10 text-emerald-600",
        "bg-amber-500/10 text-amber-600",
    ];

    const quickActions = [
        {
            href: "/admin/documents",
            icon: FileText,
            title: "Tải tài liệu",
            description: "Bổ sung tài liệu vào kho tri thức",
        },
        {
            href: "/admin/knowledge-bases",
            icon: Database,
            title: "Knowledge Base",
            description: "Quản lý kho tri thức của hệ thống",
        },
        {
            href: "/admin/users",
            icon: Users,
            title: "Người dùng",
            description: "Phân quyền và quản lý tài khoản",
        },
    ];

    return (
        <div className="flex flex-col gap-6 p-6">
            {error && (
                <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    {error}
                </div>
            )}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                    <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                        <span className="flex size-6 items-center justify-center rounded-lg bg-primary/10 text-primary">
                            <LayoutDashboard className="size-3.5" />
                        </span>
                        Tổng quan hệ thống
                    </div>
                    <h1 className="mt-3 text-2xl font-bold tracking-tight text-foreground">
                        Xin chào, {user?.username ?? "Admin"}
                    </h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Theo dõi hoạt động của trợ lý RAG và kho tri thức trong
                        một nơi.
                    </p>
                </div>
                <div className="flex items-center gap-2 self-start sm:self-auto">
                    <div className="flex items-center gap-1 rounded-lg border border-border bg-card p-1 shadow-sm">
                        {["24h", "7d", "30d"].map((p) => (
                            <Button
                                key={p}
                                variant="ghost"
                                size="xs"
                                onClick={() => setPeriod(p)}
                                className={cn(
                                    "font-medium",
                                    period === p
                                        ? "bg-primary text-primary-foreground shadow-sm hover:bg-primary hover:text-primary-foreground"
                                        : "text-muted-foreground",
                                )}
                            >
                                {p}
                            </Button>
                        ))}
                    </div>
                    <Button
                        variant="outline"
                        size="icon"
                        className="bg-card text-muted-foreground"
                        aria-label="Làm mới dữ liệu"
                        onClick={loadData}
                    >
                        <RefreshCw className="size-3.5" />
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {statCards.map((card, index) => {
                    const Icon = card.icon;
                    return (
                        <Card
                            size="sm"
                            key={card.label}
                            className="transition-shadow hover:shadow-md"
                        >
                            <CardContent className="flex flex-col gap-4">
                                <div className="flex items-start justify-between gap-3">
                                    <span className="text-sm font-medium text-muted-foreground">
                                        {card.label}
                                    </span>
                                    <span
                                        className={cn(
                                            "flex size-9 shrink-0 items-center justify-center rounded-xl",
                                            statStyles[index],
                                        )}
                                    >
                                        <Icon className="size-[18px]" />
                                    </span>
                                </div>
                                <div>
                                    <div className="text-3xl font-bold tabular-nums tracking-tight text-foreground">
                                        {card.value}
                                    </div>
                                    <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                                        <span>Toàn hệ thống</span>
                                        {card.change && (
                                            <span className="font-medium text-emerald-600">
                                                {card.change}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
                {quickActions.map((action) => {
                    const Icon = action.icon;
                    return (
                        <Link
                            key={action.href}
                            href={action.href}
                            className="group flex items-center gap-3 rounded-xl border border-border bg-card p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
                        >
                            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                                <Icon className="size-[18px]" />
                            </span>
                            <span className="min-w-0 flex-1">
                                <span className="block text-sm font-semibold text-foreground">
                                    {action.title}
                                </span>
                                <span className="block truncate text-xs text-muted-foreground">
                                    {action.description}
                                </span>
                            </span>
                            <ArrowUpRight className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
                        </Link>
                    );
                })}
            </div>

            <DashboardCharts />

            <Card className="gap-0 pb-0">
                <CardHeader className="border-b">
                    <CardTitle>Hội thoại gần đây</CardTitle>
                    <CardAction>
                        <Link
                            href="/admin/conversations"
                            className="flex items-center gap-1 text-xs font-medium text-primary transition-colors hover:text-primary/80"
                        >
                            Xem tất cả <ArrowUpRight className="size-3" />
                        </Link>
                    </CardAction>
                </CardHeader>
                <div className="flex flex-col">
                    {conversations.slice(0, 4).map((conv, i, arr) => (
                        <div key={conv.id}>
                            <div className="flex items-center gap-4 px-4 py-3.5 transition-colors hover:bg-muted/50">
                                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted">
                                    <MessageSquare className="size-4 text-muted-foreground" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <div className="truncate text-sm font-medium text-foreground">
                                        {conv.title}
                                    </div>
                                    <div className="mt-0.5 text-xs text-muted-foreground">
                                        {conv.message_count} tin nhắn ·{" "}
                                        {formatRelativeTime(conv.updated_at ?? conv.created_at)}
                                    </div>
                                </div>
                                <Link
                                    href="/admin/conversations"
                                    className="text-xs text-muted-foreground transition-colors hover:text-foreground"
                                >
                                    Xem
                                </Link>
                            </div>
                            {i < arr.length - 1 && <Separator />}
                        </div>
                    ))}
                </div>
            </Card>
        </div>
    );
}
