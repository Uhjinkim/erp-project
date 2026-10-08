export type PostType = "일반" | "공지"

export type NoticeCategory = "MANAGEMENT" | "HR" | "PAYROLL" | "DEPARTMENT"

export type Post = {
  post_id: number
  writer_employee_no: number
  writer_name: string | null
  post_type: PostType
  notice_category: NoticeCategory | null
  title: string
  content: string
  created_at: string
  updated_at: string | null
}

export type Comment = {
  comment_id: number
  post_id: number
  writer_employee_no: number
  writer_name: string | null
  parent_comment_id: number | null
  content: string
  created_at: string
  updated_at: string | null
}
