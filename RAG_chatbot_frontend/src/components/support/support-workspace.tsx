"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
    AlertTriangle,
    ArrowLeft,
    Bot,
    CheckCircle2,
    Clock,
    Headset,
    Inbox,
    Link2,
    LoaderCircle,
    MessageSquare,
    RefreshCw,
    Send,
    Sparkles,
    StickyNote,
    UserRound,
    Users,
} from "lucide-react";

import {
    assignSupportConversation,
    claimSupportConversation,
    getSupportConversation,
    getSupportStats,
    listSupportConversations,
    listSupportStaff,
    refreshSupportSummary,
    returnSupportToBot,
    sendSupportMessage,
    type Message,
    type SupportConversation,
    type SupportConversationDetail,
    type SupportScope,
    type SupportStaffOption,
    type SupportStats,
} from "@/lib/api";
import { cn, formatRelativeTime } from "@/lib/utils";
import { useAuth } from "@/lib/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

type WorkspaceMode = "staff" | "admin";

const channelMeta: Record<string, { label: string; className: string }> = {
    web: {
        label: "Web",
        className: "border-sky-500/20 bg-sky-500/10 text-sky-700",
    },
    telegram: {
        label: "Telegram",
        className: "border-cyan-500/20 bg-cyan-500/10 text-cyan-700",
    },
};

const supportModeMeta: Record<
    string,
    { label: string; className: string; dot: string }
> = {
    waiting: {
        label: "Chờ nhận",
        className: "border-amber-500/30 bg-amber-500/10 text-amber-700",
        dot: "bg-amber-500",
    },
    human: {
        label: "Đang hỗ trợ",
        className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700",
        dot: "bg-emerald-500",
    },
    bot: {
        label: "AI",
        className: "border-sky-500/20 bg-sky-500/10 text-sky-700",
        dot: "bg-sky-500",
    },
};

function getChannelMeta(channel?: string) {
    return (
        channelMeta[channel ?? "web"] ?? {
            label: channel ?? "Khác",
            className: "border-border bg-muted text-muted-foreground",
        }
    );
}

function getSupportModeMeta(mode?: string) {
    return supportModeMeta[mode ?? "bot"] ?? supportModeMeta.bot;
}

function formatWaiting(seconds: number) {
    if (seconds < 60) return `${seconds} giây`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} phút`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} giờ`;
    return `${Math.floor(hours / 24)} ngày`;
}

function escapeHtml(value: string) {
    return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatContent(content: string) {
    return escapeHtml(content)
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br/>");
}

function messageAuthor(message: Message) {
    const type = message.sender_type.toUpperCase();
    if (type === "BOT") return "Trợ lý AI";
    if (type === "STAFF") return message.sender?.username || "Nhân viên";
    if (type === "USER") return "Khách hàng";
    return "Hệ thống";
}

export function SupportWorkspace({ mode }: { mode: WorkspaceMode }) {
    const { user } = useAuth();
    const isAdmin = user?.role === "admin";

    const [scope, setScope] = useState<SupportScope>(
        mode === "admin" ? "all" : "waiting",
    );
    const [searchInput, setSearchInput] = useState("");
    const [search, setSearch] = useState("");
    const [conversations, setConversations] = useState<SupportConversation[]>([]);
    const [stats, setStats] = useState<SupportStats | null>(null);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [detail, setDetail] = useState<SupportConversationDetail | null>(null);
    const [staffOptions, setStaffOptions] = useState<SupportStaffOption[]>([]);
    const [assignTo, setAssignTo] = useState("");
    const [reply, setReply] = useState("");
    const [isInternal, setIsInternal] = useState(false);
    const [loadingList, setLoadingList] = useState(true);
    const [loadingDetail, setLoadingDetail] = useState(false);
    const [sending, setSending] = useState(false);
    const [actionBusy, setActionBusy] = useState(false);
    const [summaryBusy, setSummaryBusy] = useState(false);
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const selectedIdRef = useRef<string | null>(null);
    const autoSelectRef = useRef(false);
    const detailIdRef = useRef<string | null>(null);

    useEffect(() => {
        selectedIdRef.current = selectedId;
    }, [selectedId]);

    useEffect(() => {
        const timeout = window.setTimeout(() => setSearch(searchInput), 300);
        return () => window.clearTimeout(timeout);
    }, [searchInput]);

    useEffect(() => {
        if (!notice) return;
        const timeout = window.setTimeout(() => setNotice(""), 5000);
        return () => window.clearTimeout(timeout);
    }, [notice]);

    useEffect(() => {
        setSelectedId(null);
        selectedIdRef.current = null;
        autoSelectRef.current = false;
        setDetail(null);
    }, [scope]);

    useEffect(() => {
        if (!detail || detail.id === detailIdRef.current) return;
        detailIdRef.current = detail.id;
        setAssignTo(detail.assigned_staff_id ?? "");
    }, [detail]);

    const loadList = useCallback(
        async (silent = false) => {
            if (!silent) setLoadingList(true);
            try {
                const [items, supportStats] = await Promise.all([
                    listSupportConversations(scope, search),
                    getSupportStats(),
                ]);
                setConversations(items);
                setStats(supportStats);
                setError("");

                if (
                    !selectedIdRef.current &&
                    !autoSelectRef.current &&
                    items.length > 0
                ) {
                    autoSelectRef.current = true;
                    selectedIdRef.current = items[0].id;
                    setSelectedId(items[0].id);
                }
            } catch (e) {
                if (!silent) {
                    setError(
                        e instanceof Error
                            ? e.message
                            : "Không tải được danh sách hội thoại.",
                    );
                }
            } finally {
                if (!silent) setLoadingList(false);
            }
        },
        [scope, search],
    );

    const loadDetail = useCallback(async (id: string, silent = false) => {
        if (!silent) setLoadingDetail(true);
        try {
            const data = await getSupportConversation(id);
            if (selectedIdRef.current !== id) return;
            setDetail(data);
            setError("");
        } catch (e) {
            if (!silent) {
                setError(
                    e instanceof Error
                        ? e.message
                        : "Không tải được chi tiết hội thoại.",
                );
            }
        } finally {
            if (!silent) setLoadingDetail(false);
        }
    }, []);

    useEffect(() => {
        void loadList();
        const interval = window.setInterval(() => {
            void loadList(true);
        }, 8000);
        return () => window.clearInterval(interval);
    }, [loadList]);

    useEffect(() => {
        if (!selectedId) return;
        void loadDetail(selectedId, false);
        const interval = window.setInterval(() => {
            void loadDetail(selectedId, true);
        }, 4000);
        return () => window.clearInterval(interval);
    }, [selectedId, loadDetail]);

    useEffect(() => {
        if (!isAdmin) return;
        listSupportStaff()
            .then(setStaffOptions)
            .catch(() => setStaffOptions([]));
    }, [isAdmin]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [detail?.messages.length, selectedId]);

    const handleSelect = (id: string) => {
        if (id === selectedId) return;
        setSelectedId(id);
        selectedIdRef.current = id;
        setDetail(null);
        setReply("");
        setIsInternal(false);
    };

    const handleClaim = async () => {
        if (!detail) return;
        setActionBusy(true);
        setError("");
        try {
            await claimSupportConversation(detail.id);
            await loadDetail(detail.id, true);
            await loadList(true);
            setNotice("Bạn đã nhận hội thoại. Hãy phản hồi khách ngay nhé.");
        } catch (e) {
            setError(
                e instanceof Error ? e.message : "Không thể nhận hội thoại.",
            );
        } finally {
            setActionBusy(false);
        }
    };

    const handleAssign = async () => {
        if (!detail || !isAdmin) return;
        setActionBusy(true);
        setError("");
        try {
            await assignSupportConversation(detail.id, assignTo || null);
            await loadDetail(detail.id, true);
            await loadList(true);
            setNotice(
                assignTo ? "Đã phân công hội thoại." : "Đã đưa hội thoại về hàng đợi.",
            );
        } catch (e) {
            setError(e instanceof Error ? e.message : "Không thể phân công.");
        } finally {
            setActionBusy(false);
        }
    };

    const handleReturnToBot = async () => {
        if (!detail) return;
        const confirmed = window.confirm(
            "Kết thúc hỗ trợ và trả hội thoại về cho trợ lý AI?",
        );
        if (!confirmed) return;

        setActionBusy(true);
        setError("");
        try {
            await returnSupportToBot(detail.id);
            await loadDetail(detail.id, true);
            await loadList(true);
            setNotice("Đã kết thúc hỗ trợ. AI sẽ tiếp tục trả lời khách.");
        } catch (e) {
            setError(
                e instanceof Error
                    ? e.message
                    : "Không thể kết thúc hỗ trợ.",
            );
        } finally {
            setActionBusy(false);
        }
    };

    const handleRefreshSummary = async () => {
        if (!detail) return;
        setSummaryBusy(true);
        setError("");
        try {
            const updated = await refreshSupportSummary(detail.id);
            setDetail((prev) =>
                prev
                    ? {
                          ...prev,
                          summary: updated.summary,
                          summary_updated_at: updated.summary_updated_at,
                      }
                    : prev,
            );
            setNotice("Đã tóm tắt lại hội thoại.");
        } catch (e) {
            setError(e instanceof Error ? e.message : "Không thể tóm tắt lại.");
        } finally {
            setSummaryBusy(false);
        }
    };

    const handleSend = async () => {
        if (!detail || !reply.trim() || sending) return;
        setSending(true);
        setError("");
        try {
            const result = await sendSupportMessage(detail.id, {
                content: reply.trim(),
                is_internal: isInternal,
            });
            setReply("");
            setIsInternal(false);
            await loadDetail(detail.id, true);
            await loadList(true);
            if (result.warning) {
                setNotice(result.warning);
            } else if (isInternal) {
                setNotice("Đã lưu ghi chú nội bộ.");
            } else {
                setNotice("Đã gửi tin nhắn cho khách.");
            }
        } catch (e) {
            setError(
                e instanceof Error ? e.message : "Không gửi được tin nhắn.",
            );
        } finally {
            setSending(false);
        }
    };

    const tabs: { value: SupportScope; label: string; count?: number }[] =
        mode === "admin"
            ? [
                  { value: "all", label: "Tất cả" },
                  {
                      value: "waiting",
                      label: "Hàng đợi",
                      count: stats?.waiting_count,
                  },
                  {
                      value: "active",
                      label: "Đang hỗ trợ",
                      count: stats?.active_count,
                  },
                  { value: "closed", label: "Đã đóng" },
              ]
            : [
                  {
                      value: "waiting",
                      label: "Hàng đợi",
                      count: stats?.waiting_count,
                  },
                  {
                      value: "mine",
                      label: "Của tôi",
                      count: stats?.assigned_to_me,
                  },
              ];

    const canClaim =
        detail?.support_mode === "waiting" && detail?.resolved_at === null;
    const canReply =
        detail?.support_mode === "human" &&
        detail?.resolved_at === null &&
        (isAdmin || detail?.assigned_staff_id === user?.id);
    const isClosed = Boolean(detail?.resolved_at);

    return (
        <div className="flex h-full flex-col gap-4 p-4 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="flex size-9 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm shadow-emerald-600/20">
                            <Headset className="size-4.5" />
                        </span>
                        <div>
                            <h1 className="text-xl font-bold text-foreground">
                                {mode === "admin"
                                    ? "Hỗ trợ trực tiếp"
                                    : "Bàn hỗ trợ khách hàng"}
                            </h1>
                            <p className="text-xs text-muted-foreground">
                                {mode === "admin"
                                    ? "Theo dõi, phân công và tiếp quản các hội thoại đã chuyển cho nhân viên."
                                    : "Tiếp nhận khách đang bức xúc, xem tóm tắt và trả lời thay AI."}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <Badge
                        variant="outline"
                        className="gap-1.5 border-amber-500/30 bg-amber-500/10 text-amber-700"
                    >
                        <Clock className="size-3" />
                        {stats?.waiting_count ?? 0} đang chờ
                    </Badge>
                    <Badge
                        variant="outline"
                        className="gap-1.5 border-emerald-500/30 bg-emerald-500/10 text-emerald-700"
                    >
                        <Users className="size-3" />
                        {isAdmin
                            ? stats?.active_count ?? 0
                            : stats?.assigned_to_me ?? 0}{" "}
                        đang xử lý
                    </Badge>
                </div>
            </div>

            {(error || notice) && (
                <div
                    className={cn(
                        "flex items-center gap-2 rounded-xl border px-3 py-2 text-sm",
                        error
                            ? "border-destructive/30 bg-destructive/10 text-destructive"
                            : "border-emerald-500/30 bg-emerald-500/10 text-emerald-700",
                    )}
                >
                    {error ? (
                        <AlertTriangle className="size-4 shrink-0" />
                    ) : (
                        <CheckCircle2 className="size-4 shrink-0" />
                    )}
                    <span className="min-w-0 flex-1">{error || notice}</span>
                    <button
                        type="button"
                        onClick={() => {
                            setError("");
                            setNotice("");
                        }}
                        className="text-xs font-medium underline-offset-4 hover:underline"
                    >
                        Đóng
                    </button>
                </div>
            )}

            <div className="flex min-h-0 flex-1 flex-col gap-4 lg:grid lg:grid-cols-[360px_1fr]">
                <Card
                    className={cn(
                        "min-h-0 flex-col gap-0 overflow-hidden py-0",
                        detail ? "hidden lg:flex" : "flex",
                    )}
                >
                    <div className="border-b px-4 py-3">
                        <div className="relative">
                            <MessageSquare className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                className="pl-9 text-sm"
                                placeholder="Tìm theo tên khách, nội dung..."
                                value={searchInput}
                                onChange={(e) => setSearchInput(e.target.value)}
                            />
                        </div>
                        <div className="mt-3 flex flex-wrap gap-1.5">
                            {tabs.map((tab) => (
                                <Button
                                    key={tab.value}
                                    variant="outline"
                                    size="sm"
                                    className={cn(
                                        "h-7 gap-1.5 px-2.5 text-xs",
                                        scope === tab.value &&
                                            "border-emerald-500/30 bg-emerald-500/10 text-emerald-700",
                                    )}
                                    onClick={() => setScope(tab.value)}
                                >
                                    {tab.label}
                                    {tab.count !== undefined &&
                                        tab.count > 0 && (
                                            <span className="rounded-full bg-background px-1.5 text-[10px] font-semibold">
                                                {tab.count}
                                            </span>
                                        )}
                                </Button>
                            ))}
                        </div>
                    </div>

                    <ScrollArea className="min-h-0 flex-1">
                        {loadingList ? (
                            <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
                                <LoaderCircle className="size-4 animate-spin" />
                                Đang tải hàng đợi...
                            </div>
                        ) : conversations.length === 0 ? (
                            <div className="flex flex-col items-center gap-2 px-4 py-16 text-center">
                                <Inbox className="size-8 text-muted-foreground/30" />
                                <p className="text-sm font-medium text-foreground">
                                    Không có hội thoại
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    {scope === "waiting"
                                        ? "Khi khách bức xúc, hội thoại sẽ xuất hiện ở đây."
                                        : "Chưa có hội thoại nào trong mục này."}
                                </p>
                            </div>
                        ) : (
                            <div className="divide-y divide-border">
                                {conversations.map((conversation) => {
                                    const active = conversation.id === selectedId;
                                    const channel = getChannelMeta(
                                        conversation.channel,
                                    );
                                    const support = getSupportModeMeta(
                                        conversation.support_mode,
                                    );

                                    return (
                                        <button
                                            key={conversation.id}
                                            onClick={() =>
                                                handleSelect(conversation.id)
                                            }
                                            className={cn(
                                                "w-full px-4 py-3 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                                                active && "bg-emerald-500/5",
                                            )}
                                        >
                                            <div className="flex items-start gap-3">
                                                <div
                                                    className={cn(
                                                        "flex size-9 shrink-0 items-center justify-center rounded-xl",
                                                        active
                                                            ? "bg-emerald-500/15 text-emerald-700"
                                                            : "bg-muted text-muted-foreground",
                                                    )}
                                                >
                                                    <Headset className="size-4" />
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex items-center gap-1.5">
                                                        <span className="truncate text-sm font-semibold text-foreground">
                                                            {conversation.title ||
                                                                conversation.customer_name}
                                                        </span>
                                                        <span
                                                            className={cn(
                                                                "ml-auto size-1.5 shrink-0 rounded-full",
                                                                support.dot,
                                                            )}
                                                        />
                                                    </div>
                                                    <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                                                        <span className="truncate">
                                                            {conversation.customer_name}
                                                        </span>
                                                        <span>·</span>
                                                        <Badge
                                                            variant="outline"
                                                            className={cn(
                                                                "h-4 px-1.5 text-[10px]",
                                                                channel.className,
                                                            )}
                                                        >
                                                            {channel.label}
                                                        </Badge>
                                                        {conversation.support_mode ===
                                                            "waiting" && (
                                                            <>
                                                                <span>·</span>
                                                                <span className="shrink-0 text-amber-700">
                                                                    Chờ{" "}
                                                                    {formatWaiting(
                                                                        conversation.waiting_seconds,
                                                                    )}
                                                                </span>
                                                            </>
                                                        )}
                                                    </div>
                                                    {conversation.last_message_preview && (
                                                        <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">
                                                            {
                                                                conversation.last_message_preview
                                                            }
                                                        </p>
                                                    )}
                                                    <div className="mt-1 flex items-center gap-1.5 text-[10px] text-muted-foreground/80">
                                                        <span>
                                                            {formatRelativeTime(
                                                                conversation.last_message_at ??
                                                                    conversation.updated_at ??
                                                                    conversation.created_at,
                                                            )}
                                                        </span>
                                                        {conversation.assigned_staff_username && (
                                                            <>
                                                                <span>·</span>
                                                                <span>
                                                                    {
                                                                        conversation.assigned_staff_username
                                                                    }
                                                                </span>
                                                            </>
                                                        )}
                                                        {conversation.summary && (
                                                            <>
                                                                <span>·</span>
                                                                <span className="flex items-center gap-0.5 text-emerald-700">
                                                                    <Sparkles className="size-2.5" />
                                                                    có tóm tắt
                                                                </span>
                                                            </>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </ScrollArea>

                    <Separator />
                    <div className="flex items-center justify-between px-4 py-2.5 text-[11px] text-muted-foreground">
                        <span>{conversations.length} hội thoại</span>
                        <span>tự động cập nhật 8 giây</span>
                    </div>
                </Card>

                <Card
                    className={cn(
                        "min-h-0 flex-col gap-0 overflow-hidden py-0",
                        detail ? "flex" : "hidden lg:flex",
                    )}
                >
                    {loadingDetail && !detail ? (
                        <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
                            <LoaderCircle className="size-4 animate-spin" />
                            Đang tải hội thoại...
                        </div>
                    ) : detail ? (
                        <>
                            <div className="shrink-0 border-b px-4 py-3 sm:px-5">
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div className="flex min-w-0 items-start gap-2">
                                        <Button
                                            variant="ghost"
                                            size="icon-sm"
                                            className="lg:hidden"
                                            onClick={() => {
                                                setSelectedId(null);
                                                setDetail(null);
                                            }}
                                            aria-label="Quay lại danh sách"
                                        >
                                            <ArrowLeft />
                                        </Button>
                                        <div className="min-w-0">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <h2 className="truncate text-sm font-bold text-foreground">
                                                    {detail.title ||
                                                        detail.customer_name}
                                                </h2>
                                                <Badge
                                                    variant="outline"
                                                    className={cn(
                                                        "gap-1",
                                                        getSupportModeMeta(
                                                            detail.support_mode,
                                                        ).className,
                                                    )}
                                                >
                                                    <span
                                                        className={cn(
                                                            "size-1.5 rounded-full",
                                                            getSupportModeMeta(
                                                                detail.support_mode,
                                                            ).dot,
                                                        )}
                                                    />
                                                    {
                                                        getSupportModeMeta(
                                                            detail.support_mode,
                                                        ).label
                                                    }
                                                </Badge>
                                                <Badge
                                                    variant="outline"
                                                    className={
                                                        getChannelMeta(
                                                            detail.channel,
                                                        ).className
                                                    }
                                                >
                                                    {
                                                        getChannelMeta(
                                                            detail.channel,
                                                        ).label
                                                    }
                                                </Badge>
                                            </div>
                                            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                                <span className="flex items-center gap-1">
                                                    <UserRound className="size-3" />
                                                    {detail.customer_name}
                                                </span>
                                                {detail.customer_external_username && (
                                                    <span>
                                                        @
                                                        {
                                                            detail.customer_external_username
                                                        }
                                                    </span>
                                                )}
                                                {detail.customer_username && (
                                                    <span className="flex items-center gap-1">
                                                        <Link2 className="size-3" />
                                                        {
                                                            detail.customer_username
                                                        }
                                                    </span>
                                                )}
                                                {!detail.customer_is_linked && (
                                                    <span className="text-amber-700">
                                                        chưa liên kết tài khoản
                                                    </span>
                                                )}
                                                {detail.last_message_at && (
                                                    <span>
                                                        ·{" "}
                                                        {formatRelativeTime(
                                                            detail.last_message_at,
                                                        )}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex flex-wrap items-center gap-1.5">
                                        {canClaim && (
                                            <Button
                                                size="sm"
                                                onClick={() => void handleClaim()}
                                                disabled={actionBusy}
                                            >
                                                {actionBusy ? (
                                                    <LoaderCircle className="animate-spin" />
                                                ) : (
                                                    <Headset />
                                                )}
                                                Nhận hội thoại
                                            </Button>
                                        )}
                                        {detail.support_mode === "human" &&
                                            !isClosed && (
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() =>
                                                        void handleReturnToBot()
                                                    }
                                                    disabled={actionBusy}
                                                >
                                                    <Bot />
                                                    Kết thúc & trả về AI
                                                </Button>
                                            )}
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() =>
                                                void handleRefreshSummary()
                                            }
                                            disabled={summaryBusy}
                                        >
                                            <RefreshCw
                                                className={cn(
                                                    summaryBusy &&
                                                        "animate-spin",
                                                )}
                                            />
                                            Tóm tắt lại
                                        </Button>
                                    </div>
                                </div>

                                {isAdmin && (
                                    <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-muted/30 px-2.5 py-2">
                                        <span className="text-xs font-medium text-muted-foreground">
                                            Phân công:
                                        </span>
                                        <select
                                            value={assignTo}
                                            onChange={(e) =>
                                                setAssignTo(e.target.value)
                                            }
                                            className="h-8 min-w-44 rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                                        >
                                            <option value="">
                                                Chưa gán — đưa về hàng đợi
                                            </option>
                                            {staffOptions.map((staff) => (
                                                <option
                                                    key={staff.id}
                                                    value={staff.id}
                                                >
                                                    {staff.username} (
                                                    {staff.active_count} đang hỗ
                                                    trợ)
                                                </option>
                                            ))}
                                        </select>
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            onClick={() => void handleAssign()}
                                            disabled={actionBusy}
                                        >
                                            Lưu phân công
                                        </Button>
                                        {detail.assigned_staff_username && (
                                            <span className="text-xs text-muted-foreground">
                                                Đang phụ trách:{" "}
                                                <strong className="text-foreground">
                                                    {
                                                        detail.assigned_staff_username
                                                    }
                                                </strong>
                                            </span>
                                        )}
                                    </div>
                                )}
                            </div>

                            <div className="shrink-0 border-b bg-amber-500/5 px-4 py-2.5 sm:px-5">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex min-w-0 items-start gap-2">
                                        <Sparkles className="mt-0.5 size-3.5 shrink-0 text-amber-600" />
                                        <div className="min-w-0">
                                            <div className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                                                Tóm tắt hội thoại cho nhân viên
                                            </div>
                                            <div className="mt-0.5 text-[11px] text-muted-foreground">
                                                Lý do chuyển giao:{" "}
                                                {detail.handoff_reason ||
                                                    "Khách cần hỗ trợ"}
                                                {detail.summary_updated_at && (
                                                    <>
                                                        {" "}
                                                        · cập nhật{" "}
                                                        {formatRelativeTime(
                                                            detail.summary_updated_at,
                                                        )}
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-1.5 max-h-40 overflow-y-auto pr-1 text-sm leading-relaxed text-foreground">
                                    {detail.summary ? (
                                        <div
                                            className="whitespace-pre-line"
                                            dangerouslySetInnerHTML={{
                                                __html: formatContent(
                                                    detail.summary,
                                                ),
                                            }}
                                        />
                                    ) : (
                                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                            <LoaderCircle className="size-3.5 animate-spin" />
                                            AI đang tóm tắt cuộc hội thoại...
                                        </div>
                                    )}
                                </div>
                            </div>

                            <ScrollArea className="min-h-0 flex-1">
                                <div className="flex flex-col gap-4 p-4 sm:p-5">
                                    {detail.messages.length === 0 && (
                                        <p className="py-8 text-center text-sm text-muted-foreground">
                                            Chưa có tin nhắn.
                                        </p>
                                    )}
                                    {detail.messages.map((message) => {
                                        const type =
                                            message.sender_type.toUpperCase();

                                        if (message.is_internal) {
                                            return (
                                                <div
                                                    key={message.id}
                                                    className="mx-auto w-full max-w-2xl rounded-xl border border-dashed border-amber-500/40 bg-amber-500/10 px-3.5 py-2.5"
                                                >
                                                    <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                                                        <StickyNote className="size-3" />
                                                        Ghi chú nội bộ ·{" "}
                                                        {messageAuthor(message)}
                                                    </div>
                                                    <p className="mt-1 whitespace-pre-line text-sm text-foreground">
                                                        {message.content}
                                                    </p>
                                                    <div className="mt-1 text-[10px] text-muted-foreground">
                                                        {formatRelativeTime(
                                                            message.created_at,
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        }

                                        if (type === "SYSTEM") {
                                            return (
                                                <div
                                                    key={message.id}
                                                    className="mx-auto flex max-w-xl items-center gap-1.5 rounded-full border border-border bg-muted px-3 py-1.5 text-center text-[11px] text-muted-foreground"
                                                >
                                                    <Bot className="size-3 shrink-0" />
                                                    {message.content}
                                                </div>
                                            );
                                        }

                                        const isUser = type === "USER";
                                        const isStaff = type === "STAFF";

                                        return (
                                            <div
                                                key={message.id}
                                                className={cn(
                                                    "flex gap-2.5",
                                                    isUser && "flex-row-reverse",
                                                )}
                                            >
                                                <div className="mt-0.5 shrink-0">
                                                    {isUser ? (
                                                        <Avatar className="size-8">
                                                            <AvatarFallback className="bg-primary/15 text-xs text-primary">
                                                                <UserRound className="size-3.5" />
                                                            </AvatarFallback>
                                                        </Avatar>
                                                    ) : isStaff ? (
                                                        <div className="flex size-8 items-center justify-center rounded-full bg-emerald-600 text-white">
                                                            <Headset className="size-3.5" />
                                                        </div>
                                                    ) : (
                                                        <div className="flex size-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
                                                            <Bot className="size-3.5" />
                                                        </div>
                                                    )}
                                                </div>
                                                <div
                                                    className={cn(
                                                        "flex max-w-[80%] flex-col gap-1",
                                                        isUser
                                                            ? "items-end"
                                                            : "items-start",
                                                    )}
                                                >
                                                    {!isUser && (
                                                        <span className="text-[10px] font-medium text-muted-foreground">
                                                            {messageAuthor(
                                                                message,
                                                            )}
                                                        </span>
                                                    )}
                                                    <div
                                                        className={cn(
                                                            "px-3.5 py-2.5 text-sm leading-relaxed",
                                                            isUser
                                                                ? "rounded-2xl rounded-br-sm bg-primary text-primary-foreground"
                                                                : isStaff
                                                                  ? "rounded-2xl rounded-tl-sm border border-emerald-500/20 bg-emerald-500/10 text-foreground"
                                                                  : "rounded-2xl rounded-tl-sm border border-border bg-card text-foreground shadow-sm",
                                                        )}
                                                        dangerouslySetInnerHTML={{
                                                            __html: formatContent(
                                                                message.content,
                                                            ),
                                                        }}
                                                    />
                                                    <span className="text-[10px] text-muted-foreground/80">
                                                        {formatRelativeTime(
                                                            message.created_at,
                                                        )}
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                    <div ref={messagesEndRef} />
                                </div>
                            </ScrollArea>

                            <div className="shrink-0 border-t bg-background/80 px-4 py-3 backdrop-blur-xl sm:px-5">
                                {isClosed ? (
                                    <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                                        <CheckCircle2 className="size-4 text-emerald-600" />
                                        Hội thoại đã kết thúc. Khách đã được
                                        trả về cho trợ lý AI.
                                    </div>
                                ) : canClaim ? (
                                    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-800">
                                        <AlertTriangle className="size-4 shrink-0" />
                                        <span className="min-w-0 flex-1">
                                            Khách đang chờ. Nhận hội thoại để
                                            bắt đầu trả lời.
                                        </span>
                                        <Button
                                            size="sm"
                                            onClick={() => void handleClaim()}
                                            disabled={actionBusy}
                                        >
                                            Nhận ngay
                                        </Button>
                                    </div>
                                ) : canReply ? (
                                    <>
                                        <div className="mb-2 flex flex-wrap items-center gap-2">
                                            <Button
                                                type="button"
                                                variant={
                                                    isInternal
                                                        ? "secondary"
                                                        : "ghost"
                                                }
                                                size="sm"
                                                className={cn(
                                                    "h-7 text-xs",
                                                    isInternal &&
                                                        "bg-amber-500/15 text-amber-800",
                                                )}
                                                onClick={() =>
                                                    setIsInternal(!isInternal)
                                                }
                                            >
                                                <StickyNote />
                                                {isInternal
                                                    ? "Đang ghi chú nội bộ"
                                                    : "Ghi chú nội bộ"}
                                            </Button>
                                            <span className="text-[11px] text-muted-foreground">
                                                {isInternal
                                                    ? "Chỉ staff/admin thấy, khách không nhận được."
                                                    : detail.channel ===
                                                        "telegram"
                                                      ? "Tin nhắn sẽ được gửi qua Telegram."
                                                      : "Khách sẽ thấy tin nhắn khi tải lại hội thoại."}
                                            </span>
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="sm"
                                                className="ml-auto h-7 gap-1.5 border-emerald-500/30 text-emerald-700 hover:bg-emerald-500/10"
                                                onClick={() =>
                                                    void handleReturnToBot()
                                                }
                                                disabled={actionBusy}
                                            >
                                                {actionBusy ? (
                                                    <LoaderCircle className="animate-spin" />
                                                ) : (
                                                    <CheckCircle2 />
                                                )}
                                                Kết thúc &amp; trả về AI
                                            </Button>
                                        </div>
                                        <div
                                            className={cn(
                                                "rounded-xl border bg-card p-2 shadow-sm",
                                                isInternal
                                                    ? "border-amber-500/40"
                                                    : "border-border",
                                            )}
                                        >
                                            <div className="flex items-end gap-2">
                                                <Textarea
                                                    value={reply}
                                                    onChange={(e) =>
                                                        setReply(e.target.value)
                                                    }
                                                    onKeyDown={(e) => {
                                                        if (
                                                            e.key ===
                                                                "Enter" &&
                                                            !e.shiftKey
                                                        ) {
                                                            e.preventDefault();
                                                            void handleSend();
                                                        }
                                                    }}
                                                    rows={1}
                                                    className="max-h-[140px] min-h-[44px] resize-none overflow-y-auto border-0 bg-transparent shadow-none focus-visible:ring-0"
                                                    placeholder={
                                                        isInternal
                                                            ? "Nhập ghi chú cho đồng nghiệp..."
                                                            : "Nhập tin nhắn trả lời khách..."
                                                    }
                                                />
                                                <Button
                                                    onClick={() =>
                                                        void handleSend()
                                                    }
                                                    disabled={
                                                        !reply.trim() || sending
                                                    }
                                                    size="icon"
                                                    className="size-10 shrink-0 rounded-xl"
                                                    aria-label="Gửi tin nhắn"
                                                >
                                                    {sending ? (
                                                        <LoaderCircle className="animate-spin" />
                                                    ) : (
                                                        <Send />
                                                    )}
                                                </Button>
                                            </div>
                                        </div>
                                        <p className="mt-1.5 text-center text-[10px] text-muted-foreground/70">
                                            Enter để gửi · Shift + Enter để
                                            xuống dòng
                                        </p>
                                    </>
                                ) : (
                                    <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                                        <Headset className="size-4" />
                                        {detail.assigned_staff_username
                                            ? `Hội thoại do ${detail.assigned_staff_username} phụ trách.`
                                            : "Hội thoại chưa được phân công."}
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
                            <Headset className="size-10 text-muted-foreground/30" />
                            <h3 className="text-sm font-bold text-foreground">
                                Chọn một hội thoại
                            </h3>
                            <p className="max-w-sm text-sm text-muted-foreground">
                                Chọn khách đang chờ ở danh sách bên trái để xem
                                tóm tắt và tiếp tục trò chuyện thay AI.
                            </p>
                        </div>
                    )}
                </Card>
            </div>
        </div>
    );
}
