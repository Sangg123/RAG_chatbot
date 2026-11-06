"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
    Bot,
    CheckCircle,
    CheckCircle2,
    Eye,
    EyeOff,
    LoaderCircle,
    Lock,
    Mail,
    Sparkles,
    User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { register } from "@/lib/auth";

const benefits = [
    "Đăng ký miễn phí, bắt đầu sử dụng dễ dàng",
    "Lưu trữ và quản lý lịch sử hội thoại cá nhân",
    "Nhận câu trả lời thông minh kèm nguồn tài liệu trích dẫn",
];

export default function RegisterPage() {
    const [show, setShow] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const router = useRouter();

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            await register(username.trim(), email.trim(), password);
            setLoading(false);
            router.push("/chat");
        } catch (e) {
            setLoading(false);
            setError(
                e instanceof Error
                    ? e.message
                    : "Không thể tạo tài khoản. Vui lòng thử lại.",
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
                        Bắt đầu trong 1 phút
                    </span>

                    <h1 className="mt-6 text-4xl font-bold leading-[1.15] tracking-tight">
                        Khám phá sức mạnh AI, kết nối tri thức theo cách của bạn.
                    </h1>

                    <p className="mt-4 text-sm leading-relaxed text-primary-foreground/75">
                        Tạo tài khoản miễn phí để trò chuyện với trợ lý AI, tra cứu thông tin từ tài liệu và tận hưởng trải nghiệm hỏi đáp thông minh ngay hôm nay.
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
                            Tạo tài khoản
                        </h2>
                        <p className="mt-1.5 text-sm text-muted-foreground">
                            Chỉ mất một phút để bắt đầu sử dụng trợ lý RAG.
                        </p>
                    </div>

                    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                        <form
                            onSubmit={handleRegister}
                            className="flex flex-col gap-4"
                        >
                            <div className="flex flex-col gap-1.5">
                                <label
                                    htmlFor="reg-username"
                                    className="text-sm font-medium text-foreground"
                                >
                                    Tên đăng nhập
                                </label>
                                <div className="relative">
                                    <User
                                        size={16}
                                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                                    />
                                    <Input
                                        id="reg-username"
                                        type="text"
                                        value={username}
                                        onChange={(e) =>
                                            setUsername(e.target.value)
                                        }
                                        className="h-10 pl-9"
                                        placeholder="username"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="flex flex-col gap-1.5">
                                <label
                                    htmlFor="reg-email"
                                    className="text-sm font-medium text-foreground"
                                >
                                    Email
                                </label>
                                <div className="relative">
                                    <Mail
                                        size={16}
                                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                                    />
                                    <Input
                                        id="reg-email"
                                        type="email"
                                        value={email}
                                        onChange={(e) =>
                                            setEmail(e.target.value)
                                        }
                                        className="h-10 pl-9"
                                        placeholder="email@company.com"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="flex flex-col gap-1.5">
                                <label
                                    htmlFor="reg-password"
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
                                        id="reg-password"
                                        type={show ? "text" : "password"}
                                        value={password}
                                        onChange={(e) =>
                                            setPassword(e.target.value)
                                        }
                                        className="h-10 pl-9 pr-10"
                                        placeholder="••••••••"
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

                            {error && (
                                <p
                                    className="text-sm text-destructive"
                                    role="alert"
                                >
                                    {error}
                                </p>
                            )}

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
                                        Đang tạo tài khoản...
                                    </>
                                ) : (
                                    <>
                                        Đăng ký
                                        <CheckCircle data-icon="inline-end" />
                                    </>
                                )}
                            </Button>
                        </form>
                    </div>

                    <p className="mt-6 text-center text-sm text-muted-foreground">
                        Đã có tài khoản?{" "}
                        <Link
                            href="/login"
                            className="font-medium text-primary underline-offset-4 transition-colors hover:underline"
                        >
                            Đăng nhập
                        </Link>
                    </p>
                </div>
            </main>
        </div>
    );
}
