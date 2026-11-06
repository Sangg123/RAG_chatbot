"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
    ArrowRight,
    Bot,
    CheckCircle2,
    Eye,
    EyeOff,
    LoaderCircle,
    Lock,
    Sparkles,
    User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { login } from "@/lib/auth";

const benefits = [
    "Hỏi đáp thông minh dựa trên tài liệu nội bộ",
    "Câu trả lời minh bạch, đi kèm nguồn trích dẫn",
    "Lưu trữ hội thoại và quản lý tri thức tập trung",
];

function LoginPageContent() {
    const [show, setShow] = useState(false);
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const router = useRouter();
    const searchParams = useSearchParams();
    const redirect = searchParams.get("redirect") || "/chat";

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        if (!username.trim() || !password) {
            setLoading(false);
            setError("Vui lòng nhập tài khoản và mật khẩu.");
            return;
        }
        try {
            const user = await login(username.trim(), password);
            setLoading(false);
            router.push(user.role === "admin" ? "/admin" : redirect);
        } catch (e) {
            setLoading(false);
            setError(
                e instanceof Error
                    ? e.message
                    : "Không thể đăng nhập. Vui lòng thử lại.",
            );
        }
    };

    return (
        <div className="grid min-h-screen bg-background lg:grid-cols-2">
            <aside className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
                <div className="pointer-events-none absolute -right-24 -top-32 size-96 rounded-full bg-white/10 blur-3xl" />
                <div className="pointer-events-none absolute -bottom-32 -left-20 size-80 rounded-full bg-white/10 blur-3xl" />

                <Link
                    href="/"
                    className="relative flex items-center gap-2.5 text-primary-foreground"
                >
                    <span className="flex size-9 items-center justify-center rounded-xl bg-white/15 backdrop-blur-sm">
                        <Bot className="size-5" />
                    </span>
                    <span className="flex flex-col leading-tight">
                        <span className="text-sm font-bold">RAG ChatBot</span>
                        <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-primary-foreground/60">
                            Customer Care AI
                        </span>
                    </span>
                </Link>

                <div className="relative max-w-md">
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium">
                        <Sparkles className="size-3" />
                        Được hỗ trợ bởi RAG
                    </span>

                    <h1 className="mt-6 text-4xl font-bold leading-[1.15] tracking-tight">
                        Trợ lý AI thông minh, kết nối tri thức – nâng tầm trải nghiệm.
                    </h1>

                    <p className="mt-4 text-sm leading-relaxed text-primary-foreground/75">
                        Khám phá kho tri thức doanh nghiệp, trò chuyện với trợ lý AI và tìm kiếm câu trả lời nhanh chóng, chính xác dựa trên nguồn tài liệu đáng tin cậy.
                    </p>

                    <ul className="mt-8 space-y-3">
                        {benefits.map((benefit) => (
                            <li
                                key={benefit}
                                className="flex items-start gap-3 text-sm text-primary-foreground/85"
                            >
                                <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
                                {benefit}
                            </li>
                        ))}
                    </ul>
                </div>

                <p className="relative text-xs text-primary-foreground/50">
                    © 2026 RAG ChatBot · Đồ án chuyên ngành
                </p>
            </aside>

            <main className="flex items-center justify-center px-6 py-12">
                <div className="w-full max-w-sm">
                    <Link
                        href="/"
                        className="mb-10 flex items-center gap-2.5 lg:hidden"
                    >
                        <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                            <Bot className="size-5" />
                        </span>
                        <span className="flex flex-col leading-tight">
                            <span className="text-sm font-bold text-foreground">
                                RAG ChatBot
                            </span>
                            <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                                Customer Care AI
                            </span>
                        </span>
                    </Link>

                    <div className="mb-8">
                        <h2 className="text-2xl font-bold tracking-tight text-foreground">
                            Đăng nhập
                        </h2>
                        <p className="mt-1.5 text-sm text-muted-foreground">
                            Chào mừng trở lại! Đăng nhập để tiếp tục phiên làm
                            việc.
                        </p>
                    </div>

                    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                        <form
                            onSubmit={handleLogin}
                            className="flex flex-col gap-4"
                            autoComplete="off"
                        >
                            <div className="flex flex-col gap-1.5">
                                <label
                                    htmlFor="login-username"
                                    className="text-sm font-medium text-foreground"
                                >
                                    Tên tài khoản
                                </label>
                                <div className="relative">
                                    <User
                                        size={16}
                                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                                    />
                                    <Input
                                        id="login-username"
                                        type="text"
                                        value={username}
                                        onChange={(e) =>
                                            setUsername(e.target.value)
                                        }
                                        className="h-10 pl-9"
                                        placeholder="Nhập tên tài khoản"
                                        autoComplete="off"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="flex flex-col gap-1.5">
                                <label
                                    htmlFor="login-password"
                                    className="text-sm font-medium text-foreground"
                                >
                                    Mật khẩu
                                </label>
                                <div className="relative">
                                    <Lock
                                        size={16}
                                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                                    />
                                    <Input
                                        id="login-password"
                                        type={show ? "text" : "password"}
                                        value={password}
                                        onChange={(e) =>
                                            setPassword(e.target.value)
                                        }
                                        className="h-10 pl-9 pr-10"
                                        placeholder="Nhập mật khẩu"
                                        autoComplete="off"
                                        required
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShow(!show)}
                                        aria-label={
                                            show
                                                ? "Ẩn mật khẩu"
                                                : "Hiện mật khẩu"
                                        }
                                        className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-0.5 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                    >
                                        {show ? (
                                            <EyeOff size={16} />
                                        ) : (
                                            <Eye size={16} />
                                        )}
                                    </button>
                                </div>
                            </div>

                            <Button
                                type="submit"
                                size="lg"
                                className="mt-1 h-10 w-full"
                                disabled={loading}
                            >
                                {loading ? (
                                    <>
                                        <LoaderCircle
                                            className="animate-spin"
                                            data-icon="inline-start"
                                        />
                                        Đang đăng nhập...
                                    </>
                                ) : (
                                    <>
                                        Đăng nhập
                                        <ArrowRight data-icon="inline-end" />
                                    </>
                                )}
                            </Button>

                            {error && (
                                <p
                                    className="text-sm text-destructive"
                                    role="alert"
                                >
                                    {error}
                                </p>
                            )}
                        </form>
                    </div>

                    <p className="mt-6 text-center text-sm text-muted-foreground">
                        Chưa có tài khoản?{" "}
                        <Link
                            href="/register"
                            className="font-medium text-primary underline-offset-4 transition-colors hover:underline"
                        >
                            Đăng ký ngay
                        </Link>
                    </p>
                </div>
            </main>
        </div>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={null}>
            <LoginPageContent />
        </Suspense>
    );
}
