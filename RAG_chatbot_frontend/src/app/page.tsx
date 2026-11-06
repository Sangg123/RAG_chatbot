"use client";

import Link from "next/link";
import {
    ArrowRight,
    Bot,
    CheckCircle2,
    Database,
    FileText,
    FileUp,
    MessageSquare,
    Search,
    Send,
    ShieldCheck,
    Sparkles,
    Star,
    Zap,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogClose,
} from "@/components/ui/dialog";

const features = [
    {
        icon: Database,
        title: "Trả lời từ tài liệu nội bộ",
        description:
            "Chatbot tìm kiếm trong knowledge base của công ty trước khi trả lời, thay vì đoán mò.",
    },
    {
        icon: ShieldCheck,
        title: "Trích dẫn minh bạch",
        description:
            "Mỗi câu trả lời đều kèm nguồn và độ liên quan, giúp khách hàng và nhân viên dễ kiểm chứng.",
    },
    {
        icon: Zap,
        title: "Phản hồi tức thì 24/7",
        description:
            "Giảm thời gian chờ đợi, xử lý câu hỏi lặp lại tự động và chuyển người thật khi cần.",
    },
];

const steps = [
    {
        icon: FileUp,
        number: "01",
        title: "Tải tài liệu lên",
        description:
            "Thêm PDF, DOCX hoặc văn bản vào knowledge base. Hệ thống tự động chia nhỏ và tạo embedding.",
    },
    {
        icon: Search,
        number: "02",
        title: "Truy xuất ngữ cảnh",
        description:
            "Khi có câu hỏi, RAG tìm những đoạn tài liệu liên quan nhất để làm ngữ cảnh cho câu trả lời.",
    },
    {
        icon: MessageSquare,
        number: "03",
        title: "Trả lời kèm nguồn",
        description:
            "Chatbot tổng hợp câu trả lời tự nhiên và hiển thị nguồn trích dẫn ngay bên dưới.",
    },
];

function StartChatDialog({
    label = "Bắt đầu chat",
    size = "default",
    className,
}: {
    label?: string;
    size?: "default" | "sm" | "lg";
    className?: string;
}) {
    return (
        <Dialog>
            <DialogTrigger
                render={
                    <button
                        type="button"
                        className={buttonVariants({ size, className })}
                    />
                }
            >
                {label}
                <ArrowRight data-icon="inline-end" />
            </DialogTrigger>

            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Cần đăng nhập để chat</DialogTitle>
                    <DialogDescription>
                        Bạn cần đăng nhập trước khi bắt đầu cuộc trò chuyện với
                        chatbot.
                    </DialogDescription>
                </DialogHeader>

                <DialogFooter>
                    <DialogClose
                        render={
                            <button
                                className={buttonVariants({ variant: "outline" })}
                            />
                        }
                    >
                        Để sau
                    </DialogClose>
                    <DialogClose
                        nativeButton={false}
                        render={
                            <Link
                                href="/login?redirect=/chat"
                                className={buttonVariants({ variant: "default" })}
                            />
                        }
                    >
                        Đăng nhập
                    </DialogClose>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-background">
            <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-xl">
                <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
                    <Link href="/" className="flex items-center gap-2.5">
                        <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/30">
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

                    <nav className="hidden items-center gap-7 text-sm font-medium text-muted-foreground md:flex">
                        <a
                            href="#features"
                            className="transition-colors hover:text-foreground"
                        >
                            Tính năng
                        </a>
                        <a
                            href="#how-it-works"
                            className="transition-colors hover:text-foreground"
                        >
                            Cách hoạt động
                        </a>
                        <a
                            href="#cta"
                            className="transition-colors hover:text-foreground"
                        >
                            Bắt đầu
                        </a>
                    </nav>

                    <div className="flex items-center gap-2">
                        <Link
                            href="/login"
                            className={buttonVariants({
                                variant: "ghost",
                                size: "sm",
                                className: "max-sm:hidden",
                            })}
                        >
                            Đăng nhập
                        </Link>
                        <StartChatDialog
                            label="Bắt đầu chat"
                            size="sm"
                            className="bg-primary"
                        />
                    </div>
                </div>
            </header>

            <main>
                <section className="relative overflow-hidden">
                    <div className="pointer-events-none absolute -right-32 -top-40 size-[480px] rounded-full bg-primary/10 blur-3xl" />
                    <div className="pointer-events-none absolute -left-40 top-48 size-[360px] rounded-full bg-violet-500/10 blur-3xl" />

                    <div className="relative mx-auto grid max-w-6xl gap-14 px-4 pb-20 pt-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:pb-28 lg:pt-20">
                        <div>
                            <Badge
                                variant="secondary"
                                className="gap-1.5 rounded-full border border-primary/15 bg-primary/5 px-3 py-1 text-primary"
                            >
                                <Sparkles className="size-3" />
                                RAG-powered · Trích dẫn minh bạch
                            </Badge>

                            <h1 className="mt-6 text-4xl font-bold leading-[1.1] tracking-tight text-foreground sm:text-5xl lg:text-[3.4rem]">
                                Chatbot chăm sóc khách hàng{" "}
                                <span className="text-primary">
                                    chính xác hơn
                                </span>{" "}
                                nhờ tài liệu của bạn
                            </h1>

                            <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
                                Hệ thống RAG giúp chatbot trả lời dựa trên
                                knowledge base nội bộ, kèm nguồn trích dẫn rõ
                                ràng — nhanh, đúng và đáng tin cậy.
                            </p>

                            <div className="mt-8 flex flex-wrap items-center gap-3">
                                <StartChatDialog
                                    label="Bắt đầu chat miễn phí"
                                    size="lg"
                                    className="h-11 px-5 text-sm"
                                />
                                <Link
                                    href="/register"
                                    className={buttonVariants({
                                        variant: "outline",
                                        size: "lg",
                                        className:
                                            "h-11 gap-2 bg-card px-5 text-sm",
                                    })}
                                >
                                    Tạo tài khoản
                                    <ArrowRight className="size-4" />
                                </Link>
                            </div>

                            <div className="mt-10 flex flex-wrap items-center gap-x-7 gap-y-3 text-sm text-muted-foreground">
                                <span className="flex items-center gap-2">
                                    <CheckCircle2 className="size-4 text-emerald-500" />
                                    Trả lời 24/7
                                </span>
                                <span className="flex items-center gap-2">
                                    <CheckCircle2 className="size-4 text-emerald-500" />
                                    Không bịa đặt
                                </span>
                                <span className="flex items-center gap-2">
                                    <CheckCircle2 className="size-4 text-emerald-500" />
                                    Triển khai nhanh
                                </span>
                            </div>
                        </div>

                        <div className="relative mx-auto w-full max-w-md lg:max-w-none">
                            <div className="absolute -inset-4 rounded-[2rem] bg-linear-to-br from-primary/15 via-transparent to-violet-500/15 blur-2xl" />

                            <div className="relative rounded-2xl border border-border bg-card p-4 shadow-2xl shadow-primary/10">
                                <div className="flex items-center gap-3 border-b border-border pb-4">
                                    <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                                        <Bot className="size-5" />
                                    </span>
                                    <div className="min-w-0 flex-1">
                                        <div className="text-sm font-semibold text-foreground">
                                            Trợ lý RAG
                                        </div>
                                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                            <span className="size-1.5 rounded-full bg-emerald-500" />
                                            Đang trực tuyến
                                        </div>
                                    </div>
                                    <Badge
                                        variant="outline"
                                        className="gap-1 text-[10px]"
                                    >
                                        <Database className="size-3" />
                                        12 nguồn
                                    </Badge>
                                </div>

                                <div className="space-y-4 py-5">
                                    <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm text-primary-foreground">
                                        Chính sách đổi trả trong bao nhiêu
                                        ngày?
                                    </div>

                                    <div className="max-w-[90%] space-y-2">
                                        <div className="rounded-2xl rounded-tl-md border border-border bg-muted/40 px-4 py-3 text-sm leading-relaxed text-foreground">
                                            Theo chính sách hiện hành, bạn có
                                            thể đổi trả trong{" "}
                                            <strong>30 ngày</strong> kể từ ngày
                                            nhận hàng, với điều kiện sản phẩm
                                            còn nguyên tem mác.
                                        </div>
                                        <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
                                            <FileText className="size-3" />
                                            2 nguồn trích dẫn
                                            <ArrowRight className="size-3" />
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-muted-foreground">
                                        <Search className="size-4" />
                                        Hỏi về sản phẩm, bảo hành...
                                        <span className="ml-auto flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                                            <Send className="size-3.5" />
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="absolute -bottom-5 -left-4 hidden items-center gap-2 rounded-xl border border-border bg-card px-3.5 py-2.5 text-xs font-medium text-foreground shadow-lg sm:flex">
                                <ShieldCheck className="size-4 text-emerald-500" />
                                Trích dẫn 100%
                            </div>
                            <div className="absolute -right-3 -top-4 hidden items-center gap-2 rounded-xl border border-border bg-card px-3.5 py-2.5 text-xs font-medium text-foreground shadow-lg sm:flex">
                                <Star className="size-4 fill-amber-400 text-amber-400" />
                                4.9/5 hài lòng
                            </div>
                        </div>
                    </div>
                </section>

                <section
                    id="features"
                    className="border-y border-border bg-muted/40 py-20"
                >
                    <div className="mx-auto max-w-6xl px-4 sm:px-6">
                        <div className="max-w-2xl">
                            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
                                Tính năng
                            </p>
                            <h2 className="mt-3 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                                Mọi câu trả lời đều có căn cứ
                            </h2>
                            <p className="mt-3 text-muted-foreground">
                                Kết hợp tìm kiếm ngữ nghĩa với mô hình ngôn ngữ
                                để tạo ra trải nghiệm hỗ trợ khách hàng đáng
                                tin cậy.
                            </p>
                        </div>

                        <div className="mt-10 grid gap-5 md:grid-cols-3">
                            {features.map((feature) => {
                                const Icon = feature.icon;
                                return (
                                    <div
                                        key={feature.title}
                                        className="rounded-2xl border border-border bg-card p-6 shadow-sm transition-shadow hover:shadow-md"
                                    >
                                        <span className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                                            <Icon className="size-5" />
                                        </span>
                                        <h3 className="mt-5 text-base font-semibold text-foreground">
                                            {feature.title}
                                        </h3>
                                        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                                            {feature.description}
                                        </p>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </section>

                <section id="how-it-works" className="py-20">
                    <div className="mx-auto max-w-6xl px-4 sm:px-6">
                        <div className="mx-auto max-w-2xl text-center">
                            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
                                Cách hoạt động
                            </p>
                            <h2 className="mt-3 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                                Ba bước để có câu trả lời đáng tin
                            </h2>
                            <p className="mt-3 text-muted-foreground">
                                Toàn bộ quy trình diễn ra tự động, bạn chỉ cần
                                tải tài liệu lên một lần.
                            </p>
                        </div>

                        <div className="mt-12 grid gap-6 md:grid-cols-3">
                            {steps.map((step) => {
                                const Icon = step.icon;
                                return (
                                    <div
                                        key={step.number}
                                        className="relative rounded-2xl border border-border bg-card p-6 shadow-sm"
                                    >
                                        <span className="absolute right-5 top-5 text-3xl font-bold text-muted-foreground/15">
                                            {step.number}
                                        </span>
                                        <span className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                                            <Icon className="size-5" />
                                        </span>
                                        <h3 className="mt-5 text-base font-semibold text-foreground">
                                            {step.title}
                                        </h3>
                                        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                                            {step.description}
                                        </p>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </section>

                <section id="cta" className="pb-20">
                    <div className="mx-auto max-w-6xl px-4 sm:px-6">
                        <div className="relative overflow-hidden rounded-3xl bg-primary px-6 py-12 text-primary-foreground sm:px-12">
                            <div className="pointer-events-none absolute -right-16 -top-24 size-72 rounded-full bg-white/10 blur-2xl" />
                            <div className="pointer-events-none absolute -bottom-24 left-10 size-64 rounded-full bg-white/10 blur-2xl" />

                            <div className="relative flex flex-col items-start justify-between gap-8 lg:flex-row lg:items-center">
                                <div className="max-w-xl">
                                    <h2 className="text-3xl font-bold tracking-tight">
                                        Sẵn sàng nâng cấp chăm sóc khách hàng?
                                    </h2>
                                    <p className="mt-3 text-primary-foreground/80">
                                        Bắt đầu trò chuyện với trợ lý RAG hoặc
                                        tạo tài khoản để quản lý knowledge base
                                        của riêng bạn.
                                    </p>
                                </div>

                                <div className="flex flex-wrap gap-3">
                                    <StartChatDialog
                                        label="Chat ngay"
                                        size="lg"
                                        className="h-11 bg-white px-5 text-sm text-primary shadow-none hover:bg-white/90"
                                    />
                                    <Link
                                        href="/login"
                                        className={buttonVariants({
                                            size: "lg",
                                            className:
                                                "h-11 border border-white/25 bg-white/10 px-5 text-sm text-primary-foreground shadow-none hover:bg-white/20",
                                        })}
                                    >
                                        Đăng nhập
                                    </Link>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <footer className="border-t border-border py-8">
                <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 text-xs text-muted-foreground sm:flex-row sm:px-6">
                    <span>© 2026 RAG ChatBot</span>
                    <span>
                        Đồ án chuyên ngành · Chatbot RAG trong chăm sóc khách
                        hàng
                    </span>
                </div>
            </footer>
        </div>
    );
}
