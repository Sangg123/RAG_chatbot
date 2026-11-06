"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
    Bell,
    Bot,
    ChevronLeft,
    ChevronRight,
    Database,
    FileText,
    LayoutDashboard,
    LogOut,
    Menu,
    MessageSquare,
    Search,
    Settings,
    Users,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { logout } from "@/lib/auth";
import { useAuth } from "@/lib/use-auth";

type NavItem = {
    href: string;
    icon: typeof LayoutDashboard;
    label: string;
    exact?: boolean;
};

const navGroups: { label: string; items: NavItem[] }[] = [
    {
        label: "Tổng quan",
        items: [
            {
                href: "/admin",
                icon: LayoutDashboard,
                label: "Dashboard",
                exact: true,
            },
        ],
    },
    {
        label: "Quản lý",
        items: [
            {
                href: "/admin/knowledge-bases",
                icon: Database,
                label: "Knowledge Bases",
            },
            { href: "/admin/documents", icon: FileText, label: "Tài liệu" },
            {
                href: "/admin/conversations",
                icon: MessageSquare,
                label: "Hội thoại",
            },
            { href: "/admin/users", icon: Users, label: "Người dùng" },
        ],
    },
    {
        label: "Hệ thống",
        items: [{ href: "/admin/settings", icon: Settings, label: "Cài đặt" }],
    },
];

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const [collapsed, setCollapsed] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const pathname = usePathname();
    const router = useRouter();
    const { user: currentUser, authenticated, admin } = useAuth();

    const isActive = (href: string, exact?: boolean) => {
        if (exact) return pathname === href;
        return pathname.startsWith(href);
    };

    const currentLabel =
        navGroups
            .flatMap((group) => group.items)
            .find((item) => isActive(item.href, item.exact))?.label ??
        "Quản trị";

    const handleLogout = () => {
        logout();
        router.push("/login");
    };

    useEffect(() => {
        if (authenticated && !admin) {
            router.replace("/login");
        }
    }, [authenticated, admin, router]);

    if (!currentUser) {
        return null;
    }

    const sidebarContent = (
        collapsed: boolean,
        onNavigate?: () => void,
        showCollapse = true,
    ) => (
        <>
            <div
                className={cn(
                    "flex h-16 shrink-0 items-center gap-2.5 border-b border-border px-4",
                    collapsed && "justify-center px-0",
                )}
            >
                <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/25">
                    <Bot className="size-5" />
                </span>
                {!collapsed && (
                    <div className="min-w-0 leading-tight">
                        <div className="truncate text-sm font-bold text-foreground">
                            RAG ChatBot
                        </div>
                        <div className="truncate text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                            Admin workspace
                        </div>
                    </div>
                )}
            </div>

            <ScrollArea className="flex-1">
                <nav className="flex flex-col gap-5 px-3 py-4">
                    {navGroups.map((group) => (
                        <div key={group.label}>
                            {!collapsed && (
                                <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                    {group.label}
                                </div>
                            )}
                            <div className="flex flex-col gap-0.5">
                                {group.items.map((item) => {
                                    const active = isActive(
                                        item.href,
                                        item.exact,
                                    );
                                    const linkContent = (
                                        <Link
                                            href={item.href}
                                            onClick={onNavigate}
                                            className={cn(
                                                "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                                                collapsed &&
                                                    "justify-center px-0",
                                                active
                                                    ? "bg-primary/10 text-primary"
                                                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                                            )}
                                        >
                                            <item.icon className="size-[18px] shrink-0" />
                                            {!collapsed && (
                                                <span className="truncate">
                                                    {item.label}
                                                </span>
                                            )}
                                            {!collapsed && active && (
                                                <span className="ml-auto size-1.5 rounded-full bg-primary" />
                                            )}
                                        </Link>
                                    );

                                    return (
                                        <div key={item.href}>
                                            {collapsed ? (
                                                <Tooltip>
                                                    <TooltipTrigger
                                                        render={linkContent}
                                                    />
                                                    <TooltipContent side="right">
                                                        {item.label}
                                                    </TooltipContent>
                                                </Tooltip>
                                            ) : (
                                                linkContent
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </nav>
            </ScrollArea>

            <div
                className={cn(
                    "border-t border-border p-3",
                    collapsed && "flex flex-col items-center gap-2",
                )}
            >
                <div
                    className={cn(
                        "flex items-center gap-3 rounded-xl p-2",
                        !collapsed && "hover:bg-muted",
                    )}
                >
                    <Avatar className="size-9">
                        <AvatarFallback className="bg-primary text-xs font-bold text-primary-foreground">
                            {currentUser.username.charAt(0).toUpperCase()}
                        </AvatarFallback>
                    </Avatar>
                    {!collapsed && (
                        <>
                            <div className="min-w-0 flex-1">
                                <div className="truncate text-sm font-medium text-foreground">
                                    {currentUser.username}
                                </div>
                                <div className="truncate text-xs text-muted-foreground">
                                    {currentUser.email}
                                </div>
                            </div>
                            <Tooltip>
                                <TooltipTrigger
                                    render={
                                        <Button
                                            variant="ghost"
                                            size="icon-sm"
                                            className="text-muted-foreground hover:text-destructive"
                                            onClick={handleLogout}
                                            aria-label="Đăng xuất"
                                        >
                                            <LogOut />
                                        </Button>
                                    }
                                />
                                <TooltipContent>Đăng xuất</TooltipContent>
                            </Tooltip>
                        </>
                    )}
                </div>

                {collapsed && (
                    <Tooltip>
                        <TooltipTrigger
                            render={
                                <Button
                                    variant="ghost"
                                    size="icon-sm"
                                    className="text-muted-foreground hover:text-destructive"
                                    onClick={handleLogout}
                                    aria-label="Đăng xuất"
                                >
                                    <LogOut />
                                </Button>
                            }
                        />
                        <TooltipContent side="right">
                            Đăng xuất
                        </TooltipContent>
                    </Tooltip>
                )}
            </div>

            {showCollapse && (
                <div className="hidden border-t border-border p-2 md:flex md:justify-end">
                    <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => setCollapsed(!collapsed)}
                        className="text-muted-foreground"
                        aria-label={
                            collapsed ? "Mở rộng menu" : "Thu gọn menu"
                        }
                    >
                        {collapsed ? <ChevronRight /> : <ChevronLeft />}
                    </Button>
                </div>
            )}
        </>
    );

    return (
        <div className="flex h-screen overflow-hidden bg-background">
            <aside
                className={cn(
                    "hidden shrink-0 flex-col border-r border-border bg-card transition-[width] duration-300 ease-out md:flex",
                    collapsed ? "w-[76px]" : "w-64",
                )}
            >
                {sidebarContent(collapsed)}
            </aside>

            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
                <SheetContent
                    side="left"
                    className="w-72 bg-card p-0"
                >
                    <SheetTitle className="sr-only">
                        Menu quản trị
                    </SheetTitle>
                    {sidebarContent(false, () => setMobileOpen(false), false)}
                </SheetContent>
            </Sheet>

            <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
                <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-xl sm:px-6">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="md:hidden"
                        onClick={() => setMobileOpen(true)}
                        aria-label="Mở menu"
                    >
                        <Menu />
                    </Button>

                    <div className="flex min-w-0 items-center gap-1.5 text-sm">
                        <span className="text-xs font-medium text-muted-foreground">
                            Admin
                        </span>
                        <ChevronRight className="size-3 text-muted-foreground" />
                        <span className="truncate font-semibold text-foreground">
                            {currentLabel}
                        </span>
                    </div>

                    <div className="relative ml-auto hidden w-full max-w-xs md:block">
                        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            placeholder="Tìm kiếm nhanh..."
                            className="h-9 bg-card pl-9"
                            aria-label="Tìm kiếm"
                        />
                    </div>

                    <div className="ml-auto flex items-center gap-2 md:ml-0">
                        <Button
                            variant="outline"
                            size="sm"
                            nativeButton={false}
                            render={<Link href="/chat" />}
                            className="gap-2 bg-card max-sm:hidden"
                        >
                            <MessageSquare data-icon="inline-start" />
                            Mở Chat
                        </Button>

                        <Tooltip>
                            <TooltipTrigger
                                render={
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="relative text-muted-foreground"
                                        aria-label="Thông báo"
                                    >
                                        <Bell className="size-[18px]" />
                                        <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-destructive" />
                                    </Button>
                                }
                            />
                            <TooltipContent>Thông báo</TooltipContent>
                        </Tooltip>

                        <Separator
                            orientation="vertical"
                            className="mx-1 hidden h-8 sm:block"
                        />

                        <div className="flex items-center gap-2.5">
                            <Avatar>
                                <AvatarFallback className="bg-primary text-xs font-bold text-primary-foreground">
                                    {currentUser.username
                                        .charAt(0)
                                        .toUpperCase()}
                                </AvatarFallback>
                            </Avatar>
                            <div className="hidden md:block">
                                <div className="text-sm font-medium text-foreground">
                                    {currentUser.username}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                    {currentUser.email}
                                </div>
                            </div>
                        </div>
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto bg-muted/30">
                    {children}
                </main>
            </div>
        </div>
    );
}
