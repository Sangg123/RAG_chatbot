-- =============================================================================
-- RAG Chatbot - Du lieu mau (10 ban ghi cho moi bang)
-- Database dich: rag_chatbot
-- Chay SAU khi da chay file 01_create_tables.sql
--
-- Tai khoan mau:
--   admin      / admin123
--   cac user   / password123
--
-- Luu y: embedding cua document_chunks trong file nay la vector gia lap
-- 768 chieu (dung de test giao dien). Muon tim kiem ngu nghia that, hay
-- upload tai lieu qua API de he thong tao embedding bang Ollama.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. users (10 ban ghi)
-- ---------------------------------------------------------------------------
INSERT INTO users (id, username, email, hashed_password, role, is_active, token_version, created_at) VALUES
('00000000-0000-0000-0000-000000000001', 'admin',         'admin@company.com',     '$2b$12$Ig4luvJDVurqGe55yBz62.mpaEWuKYCH1VxeiHtQB3qJ6G8Da9BCC', 'admin', TRUE, 0, '2026-01-02 08:00:00+07'),
('11111111-1111-1111-1111-111111111001', 'nguyen.van.an', 'an.nguyen@company.com', '$2b$12$029RT/kJDFB7YC8MhdKogelrma4lDmICJOm3kLI1i4yAvLbbVHtQ2', 'user',  TRUE, 0, '2026-01-10 09:15:00+07'),
('11111111-1111-1111-1111-111111111002', 'tran.thi.binh', 'binh.tran@company.com', '$2b$12$029RT/kJDFB7YC8MhdKogelrma4lDmICJOm3kLI1i4yAvLbbVHtQ2', 'user',  TRUE, 0, '2026-01-12 10:30:00+07'),
('11111111-1111-1111-1111-111111111003', 'le.hoang.cuong', 'cuong.le@company.com', '$2b$12$029RT/kJDFB7YC8MhdKogelrma4lDmICJOm3kLI1i4yAvLbbVHtQ2', 'user',  TRUE, 0, '2026-01-15 14:05:00+07'),
('11111111-1111-1111-1111-111111111004', 'pham.minh.duc', 'duc.pham@company.com', '$2b$12$029RT/kJDFB7YC8MhdKogelrma4lDmICJOm3kLI1i4yAvLbbVHtQ2', 'user',  TRUE, 0, '2026-01-18 08:45:00+07'),
('11111111-1111-1111-1111-111111111005', 'hoang.thu.ha',  'ha.hoang@company.com', '$2b$12$029RT/kJDFB7YC8MhdKogelrma4lDmICJOm3kLI1i4yAvLbbVHtQ2', 'user',  TRUE, 0, '2026-01-20 11:20:00+07'),
('11111111-1111-1111-1111-111111111006', 'vo.quoc.huy',   'huy.vo@company.com',   '$2b$12$029RT/kJDFB7YC8MhdKogelrma4lDmICJOm3kLI1i4yAvLbbVHtQ2', 'user',  TRUE, 0, '2026-01-22 15:10:00+07'),
('11111111-1111-1111-1111-111111111007', 'dang.thi.lan',  'lan.dang@company.com', '$2b$12$029RT/kJDFB7YC8MhdKogelrma4lDmICJOm3kLI1i4yAvLbbVHtQ2', 'user',  TRUE, 0, '2026-01-25 09:00:00+07'),
('11111111-1111-1111-1111-111111111008', 'bui.anh.minh',  'minh.bui@company.com', '$2b$12$029RT/kJDFB7YC8MhdKogelrma4lDmICJOm3kLI1i4yAvLbbVHtQ2', 'user',  TRUE, 0, '2026-01-28 13:40:00+07'),
('11111111-1111-1111-1111-111111111009', 'do.thanh.nam',  'nam.do@company.com',   '$2b$12$029RT/kJDFB7YC8MhdKogelrma4lDmICJOm3kLI1i4yAvLbbVHtQ2', 'user',  FALSE, 0, '2026-02-01 16:25:00+07')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. knowledge_bases (10 ban ghi)
-- ---------------------------------------------------------------------------
INSERT INTO knowledge_bases (id, name, description, created_at) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa001', 'Chính sách nhân sự',               'Quy định về nghỉ phép, chấm công, làm việc từ xa và phúc lợi nhân viên.', '2026-02-01 09:00:00+07'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa002', 'Quy trình IT và bảo mật',          'Hướng dẫn quản lý tài khoản, mật khẩu, sao lưu và ứng cứu sự cố.',        '2026-02-03 10:15:00+07'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa003', 'Tài liệu sản phẩm RAG Chatbot',    'Tính năng, kiến trúc và hướng dẫn sử dụng hệ thống RAG Chatbot.',          '2026-02-05 13:30:00+07'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa004', 'Quy trình chăm sóc khách hàng',    'Kịch bản phản hồi, phân loại khiếu nại và cam kết chất lượng dịch vụ.',    '2026-02-10 08:45:00+07'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa005', 'Chính sách tài chính và chi phí',  'Quy định tạm ứng, hoàn ứng, mua sắm và quản lý ngân sách nội bộ.',        '2026-02-12 15:20:00+07'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa006', 'Hướng dẫn vận hành hệ thống',      'Triển khai, giám sát, xử lý sự cố và quy trình bàn giao ca trực.',        '2026-02-15 08:30:00+07'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa007', 'Tiêu chuẩn chất lượng tài liệu',   'Quy chuẩn soạn thảo, số hóa, đặt tên và kiểm duyệt tài liệu nội bộ.',     '2026-02-18 13:00:00+07'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa008', 'Đào tạo nhân viên mới',            'Lộ trình onboarding 30-60-90 ngày và tài liệu hướng dẫn cho nhân viên.',  '2026-02-20 09:45:00+07'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa009', 'Quy định bảo mật dữ liệu',         'Phân loại dữ liệu, quyền truy cập và yêu cầu mã hóa thông tin nội bộ.',   '2026-02-22 14:50:00+07'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa010', 'Kho câu hỏi thường gặp (FAQ)',     'Tổng hợp câu hỏi và câu trả lời mẫu cho nhân viên và khách hàng.',        '2026-02-25 10:10:00+07')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. documents (10 ban ghi)
-- ---------------------------------------------------------------------------
INSERT INTO documents (id, knowledge_base_id, filename, file_type, file_url, upload_status, created_at) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa001', 'chinh_sach_nhan_su_2026.pdf',           'pdf',  '/app/storage/uploads/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa001/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001_chinh_sach_nhan_su_2026.pdf',           'COMPLETED',  '2026-02-01 10:00:00+07'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa002', 'quy_trinh_it_bao_mat.docx',              'docx', '/app/storage/uploads/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa002/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb002_quy_trinh_it_bao_mat.docx',              'COMPLETED',  '2026-02-03 11:20:00+07'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb003', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa003', 'huong_dan_su_dung_rag_chatbot.pdf',      'pdf',  '/app/storage/uploads/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa003/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb003_huong_dan_su_dung_rag_chatbot.pdf',      'COMPLETED',  '2026-02-05 14:00:00+07'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb004', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa004', 'quy_trinh_cham_soc_khach_hang.docx',     'docx', '/app/storage/uploads/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa004/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb004_quy_trinh_cham_soc_khach_hang.docx',     'COMPLETED',  '2026-02-10 09:30:00+07'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb005', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa005', 'chinh_sach_tai_chinh_noi_bo.xlsx',       'xlsx', '/app/storage/uploads/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa005/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb005_chinh_sach_tai_chinh_noi_bo.xlsx',       'COMPLETED',  '2026-02-12 16:10:00+07'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb006', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa006', 'huong_dan_van_hanh_he_thong.md',         'md',   '/app/storage/uploads/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa006/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb006_huong_dan_van_hanh_he_thong.md',         'COMPLETED',  '2026-02-15 08:45:00+07'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb007', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa007', 'tieu_chuan_chat_luong_tai_lieu.docx',    'docx', '/app/storage/uploads/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa007/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb007_tieu_chuan_chat_luong_tai_lieu.docx',    'COMPLETED',  '2026-02-18 13:25:00+07'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb008', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa008', 'lo_trinh_dao_tao_nhan_vien_moi.pdf',     'pdf',  '/app/storage/uploads/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa008/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb008_lo_trinh_dao_tao_nhan_vien_moi.pdf',     'COMPLETED',  '2026-02-20 10:05:00+07'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb009', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa009', 'quy_dinh_bao_mat_du_lieu_v2.pdf',        'pdf',  '/app/storage/uploads/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa009/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb009_quy_dinh_bao_mat_du_lieu_v2.pdf',        'COMPLETED',  '2026-02-22 15:40:00+07'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb010', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa010', 'faq_noi_bo.txt',                         'txt',  '/app/storage/uploads/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa010/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb010_faq_noi_bo.txt',                         'PENDING',    '2026-11-05 08:00:00+07')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. document_chunks (10 ban ghi)
--    embedding = vector 768 chieu sinh tu cong thuc co dinh (du lieu gia lap)
-- ---------------------------------------------------------------------------
INSERT INTO document_chunks (id, document_id, content, embedding, chunk_index)
SELECT
    v.id::uuid,
    v.document_id::uuid,
    v.content,
    (
        SELECT array_agg((((v.seed * 17 + g.i * 29) % 101)::double precision / 101.0)::real ORDER BY g.i)
        FROM generate_series(1, 768) AS g(i)
    )::vector,
    v.chunk_index
FROM (VALUES
    ('cccccccc-cccc-cccc-cccc-ccccccccc001', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001',
     'Theo Chính sách nhân sự 2026, nhân viên chính thức được hưởng 12 ngày nghỉ phép có lương mỗi năm. Nhân viên làm việc dưới 12 tháng được tính theo tỷ lệ thời gian làm việc. Nghỉ phép cần đăng ký trước ít nhất 3 ngày làm việc qua hệ thống HRM và được quản lý trực tiếp phê duyệt. Tối đa 5 ngày phép chưa sử dụng được chuyển sang năm sau.', 0, 1),
    ('cccccccc-cccc-cccc-cccc-ccccccccc002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb002',
     'Mật khẩu tài khoản công ty phải có tối thiểu 12 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt. Người dùng không được dùng lại mật khẩu của 5 lần thay đổi gần nhất. Khi quên mật khẩu, nhân viên truy cập cổng self-service hoặc liên hệ bộ phận IT Helpdesk qua số nội bộ 108 để được xác minh danh tính và cấp lại.', 0, 2),
    ('cccccccc-cccc-cccc-cccc-ccccccccc003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb003',
     'Hệ thống RAG Chatbot hỗ trợ tải lên các định dạng PDF, DOCX, TXT và Markdown. Tài liệu sau khi tải lên sẽ được trích xuất văn bản, chia nhỏ thành các đoạn (chunk) và tạo embedding bằng mô hình embeddinggemma. Kích thước mỗi chunk mặc định là 1000 ký tự với độ chồng lấp 200 ký tự. Dung lượng tệp tối đa là 20 MB.', 0, 3),
    ('cccccccc-cccc-cccc-cccc-ccccccccc004', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb004',
     'Khi nhận khiếu nại qua email, nhân viên chăm sóc khách hàng phải phản hồi xác nhận trong vòng 2 giờ làm việc và cung cấp mã ticket. Mọi khiếu nại được phân loại theo mức độ ưu tiên: P1 xử lý trong 4 giờ, P2 trong 24 giờ, P3 trong 3 ngày làm việc. Trường hợp vượt thẩm quyền phải chuyển ngay cho trưởng nhóm.', 0, 4),
    ('cccccccc-cccc-cccc-cccc-ccccccccc005', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb005',
     'Quy trình tạm ứng chi phí công tác gồm bốn bước: (1) nhân viên tạo đề nghị trên hệ thống tài chính trước 5 ngày làm việc; (2) quản lý trực tiếp phê duyệt; (3) kế toán kiểm tra hạn mức và giải ngân trong 2 ngày; (4) hoàn ứng trong 15 ngày kể từ ngày kết thúc chuyến công tác, kèm hóa đơn hợp lệ.', 0, 5),
    ('cccccccc-cccc-cccc-cccc-ccccccccc006', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb006',
     'Để kiểm tra trạng thái hệ thống, truy cập endpoint /health của backend hoặc xem dashboard giám sát. Khi phát hiện sự cố, kỹ sư trực ca tạo incident với mức độ Sev1 đến Sev4, thông báo trong kênh #incident và cập nhật timeline mỗi 30 phút cho đến khi khắc phục. Sự cố Sev1 yêu cầu phản hồi trong 15 phút.', 0, 6),
    ('cccccccc-cccc-cccc-cccc-ccccccccc007', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb007',
     'Tài liệu số hóa phải tuân theo quy chuẩn đặt tên: chữ thường, không dấu, phân tách bằng dấu gạch dưới, kèm phiên bản và ngày ban hành. Nội dung phải có tiêu đề rõ ràng, mục lục, bảng biểu được gắn nhãn và trích dẫn nguồn. Tài liệu trước khi đưa vào kho tri thức phải được kiểm duyệt bởi chủ sở hữu nội dung.', 0, 7),
    ('cccccccc-cccc-cccc-cccc-ccccccccc008', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb008',
     'Lộ trình đào tạo nhân viên mới kéo dài 90 ngày. 30 ngày đầu tập trung vào giới thiệu công ty, quy trình làm việc và công cụ nội bộ. Giai đoạn 31 đến 60 ngày nhân viên tham gia dự án thực tế dưới sự hướng dẫn của mentor. Giai đoạn 61 đến 90 ngày đánh giá năng lực và xây dựng mục tiêu cá nhân cho quý tiếp theo.', 0, 8),
    ('cccccccc-cccc-cccc-cccc-ccccccccc009', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb009',
     'Dữ liệu nội bộ được phân thành bốn cấp: Công khai, Nội bộ, Mật và Tối mật. Dữ liệu Mật chỉ được truy cập bởi nhân sự được cấp quyền và phải mã hóa khi lưu trữ. Dữ liệu Tối mật yêu cầu phê duyệt của Ban Giám đốc, ghi nhật ký truy cập và không được phép sao chép ra thiết bị cá nhân.', 0, 9),
    ('cccccccc-cccc-cccc-cccc-ccccccccc010', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001',
     'Nhân viên chấm công bằng thẻ từ hoặc ứng dụng mobile khi bắt đầu và kết thúc ngày làm việc. Giờ làm việc tiêu chuẩn là 8 giờ mỗi ngày, từ 08:30 đến 17:30, nghỉ trưa 1 giờ. Đi muộn quá 15 phút sẽ bị ghi nhận; trường hợp đặc biệt cần gửi giải trình cho quản lý trong vòng 24 giờ.', 0, 1)
) AS v(id, document_id, content, chunk_index, seed)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. conversations (10 ban ghi)
-- ---------------------------------------------------------------------------
INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES
('dddddddd-dddd-dddd-dddd-ddddddddd001', '00000000-0000-0000-0000-000000000001', 'Quy định nghỉ phép năm 2026',              '2026-10-01 08:15:00+07', '2026-10-01 08:16:00+07'),
('dddddddd-dddd-dddd-dddd-ddddddddd002', '11111111-1111-1111-1111-111111111001', 'Cách đặt lại mật khẩu tài khoản',          '2026-10-05 09:00:00+07', '2026-10-05 09:01:00+07'),
('dddddddd-dddd-dddd-dddd-ddddddddd003', '11111111-1111-1111-1111-111111111002', 'RAG Chatbot hỗ trợ những định dạng nào?',   '2026-10-12 14:20:00+07', '2026-10-12 14:21:00+07'),
('dddddddd-dddd-dddd-dddd-ddddddddd004', '11111111-1111-1111-1111-111111111003', 'Quy trình xử lý khiếu nại của khách hàng', '2026-10-20 10:05:00+07', '2026-10-20 10:06:00+07'),
('dddddddd-dddd-dddd-dddd-ddddddddd005', '11111111-1111-1111-1111-111111111004', 'Thủ tục tạm ứng chi phí công tác',         '2026-10-28 16:40:00+07', '2026-10-28 16:41:00+07'),
('dddddddd-dddd-dddd-dddd-ddddddddd006', '11111111-1111-1111-1111-111111111005', 'Cách kiểm tra trạng thái dịch vụ backend', '2026-11-01 09:30:00+07', NULL),
('dddddddd-dddd-dddd-dddd-ddddddddd007', '11111111-1111-1111-1111-111111111006', 'Tiêu chuẩn đặt tên tệp tài liệu',          '2026-11-02 11:10:00+07', NULL),
('dddddddd-dddd-dddd-dddd-ddddddddd008', '11111111-1111-1111-1111-111111111007', 'Lộ trình đào tạo 30 ngày đầu',             '2026-11-03 15:45:00+07', NULL),
('dddddddd-dddd-dddd-dddd-ddddddddd009', '11111111-1111-1111-1111-111111111008', 'Dữ liệu nội bộ được phân loại thế nào?',   '2026-11-04 10:20:00+07', NULL),
('dddddddd-dddd-dddd-dddd-ddddddddd010', '11111111-1111-1111-1111-111111111009', 'Câu hỏi thường gặp về bảo mật tài khoản',  '2026-11-05 08:05:00+07', NULL)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. messages (10 ban ghi)
-- ---------------------------------------------------------------------------
INSERT INTO messages (id, conversation_id, sender_type, content, rating, feedback_text, created_at) VALUES
('eeeeeeee-eeee-eeee-eeee-eeeeeeeee001', 'dddddddd-dddd-dddd-dddd-ddddddddd001', 'USER', 'Nhân viên chính thức có bao nhiêu ngày nghỉ phép năm?', NULL, NULL, '2026-10-01 08:15:30+07'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeee002', 'dddddddd-dddd-dddd-dddd-ddddddddd001', 'BOT',  'Nhân viên chính thức được hưởng 12 ngày nghỉ phép có lương mỗi năm. Bạn cần đăng ký trước ít nhất 3 ngày làm việc trên hệ thống HRM để quản lý trực tiếp phê duyệt.', 5, 'Rõ ràng và đúng chính sách.', '2026-10-01 08:16:05+07'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeee003', 'dddddddd-dddd-dddd-dddd-ddddddddd002', 'USER', 'Tôi quên mật khẩu, cần làm gì để đặt lại?', NULL, NULL, '2026-10-05 09:00:20+07'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeee004', 'dddddddd-dddd-dddd-dddd-ddddddddd002', 'BOT',  'Bạn có thể đặt lại mật khẩu tại cổng self-service. Nếu không đăng nhập được, hãy liên hệ IT Helpdesk qua số nội bộ 108 để được xác minh danh tính và cấp lại mật khẩu.', 5, NULL, '2026-10-05 09:01:02+07'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeee005', 'dddddddd-dddd-dddd-dddd-ddddddddd003', 'USER', 'Hệ thống RAG Chatbot hỗ trợ tải lên những định dạng tài liệu nào?', NULL, NULL, '2026-10-12 14:20:15+07'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeee006', 'dddddddd-dddd-dddd-dddd-ddddddddd003', 'BOT',  'Hệ thống hỗ trợ PDF, DOCX, TXT và Markdown. Sau khi tải lên, tài liệu được trích xuất, chia chunk và tạo embedding để phục vụ tìm kiếm ngữ nghĩa.', 4, 'Cần bổ sung dung lượng tối đa.', '2026-10-12 14:21:00+07'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeee007', 'dddddddd-dddd-dddd-dddd-ddddddddd004', 'USER', 'Khi khách hàng gửi khiếu nại qua email thì xử lý thế nào?', NULL, NULL, '2026-10-20 10:05:10+07'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeee008', 'dddddddd-dddd-dddd-dddd-ddddddddd004', 'BOT',  'Khi nhận khiếu nại qua email, hãy phản hồi xác nhận trong 2 giờ làm việc và cấp mã ticket. Phân loại P1, P2, P3 tương ứng thời hạn 4 giờ, 24 giờ và 3 ngày làm việc.', 5, 'Hướng dẫn dễ hiểu.', '2026-10-20 10:06:15+07'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeee009', 'dddddddd-dddd-dddd-dddd-ddddddddd005', 'USER', 'Quy trình tạm ứng chi phí công tác gồm những bước nào?', NULL, NULL, '2026-10-28 16:40:05+07'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeee010', 'dddddddd-dddd-dddd-dddd-ddddddddd005', 'BOT',  'Quy trình gồm: tạo đề nghị trước 5 ngày làm việc, quản lý phê duyệt, kế toán giải ngân trong 2 ngày và hoàn ứng trong 15 ngày kèm hóa đơn hợp lệ.', NULL, NULL, '2026-10-28 16:41:20+07')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 7. message_citations (10 ban ghi)
-- ---------------------------------------------------------------------------
INSERT INTO message_citations (id, message_id, chunk_id, relevance_score) VALUES
('ffffffff-ffff-ffff-ffff-fffffffff001', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeee002', 'cccccccc-cccc-cccc-cccc-ccccccccc001', 0.93),
('ffffffff-ffff-ffff-ffff-fffffffff002', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeee002', 'cccccccc-cccc-cccc-cccc-ccccccccc010', 0.82),
('ffffffff-ffff-ffff-ffff-fffffffff003', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeee004', 'cccccccc-cccc-cccc-cccc-ccccccccc002', 0.95),
('ffffffff-ffff-ffff-ffff-fffffffff004', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeee004', 'cccccccc-cccc-cccc-cccc-ccccccccc009', 0.76),
('ffffffff-ffff-ffff-ffff-fffffffff005', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeee006', 'cccccccc-cccc-cccc-cccc-ccccccccc003', 0.94),
('ffffffff-ffff-ffff-ffff-fffffffff006', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeee006', 'cccccccc-cccc-cccc-cccc-ccccccccc007', 0.71),
('ffffffff-ffff-ffff-ffff-fffffffff007', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeee008', 'cccccccc-cccc-cccc-cccc-ccccccccc004', 0.91),
('ffffffff-ffff-ffff-ffff-fffffffff008', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeee008', 'cccccccc-cccc-cccc-cccc-ccccccccc006', 0.69),
('ffffffff-ffff-ffff-ffff-fffffffff009', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeee010', 'cccccccc-cccc-cccc-cccc-ccccccccc005', 0.92),
('ffffffff-ffff-ffff-ffff-fffffffff010', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeee010', 'cccccccc-cccc-cccc-cccc-ccccccccc008', 0.66)
ON CONFLICT (id) DO NOTHING;

COMMIT;

-- ---------------------------------------------------------------------------
-- Kiem tra so ban ghi sau khi insert
-- ---------------------------------------------------------------------------
SELECT 'users'             AS table_name, COUNT(*) AS rows FROM users
UNION ALL SELECT 'knowledge_bases',    COUNT(*) FROM knowledge_bases
UNION ALL SELECT 'documents',          COUNT(*) FROM documents
UNION ALL SELECT 'document_chunks',    COUNT(*) FROM document_chunks
UNION ALL SELECT 'conversations',      COUNT(*) FROM conversations
UNION ALL SELECT 'messages',           COUNT(*) FROM messages
UNION ALL SELECT 'message_citations',  COUNT(*) FROM message_citations
ORDER BY table_name;
