export type PostType = "일반" | "공지"

export type NoticeCategory = "MANAGEMENT" | "HR" | "PAYROLL"

type ViewerPermissions = {
  can_edit: boolean
  can_delete: boolean
}

export type Post = ViewerPermissions & {
  post_id: number
  writer_employee_no: number
  writer_name: string | null
  post_type: PostType
  notice_category: NoticeCategory | null
  title: string
  content: string
  comment_count: number
  created_at: string
  updated_at: string | null
}

export type Comment = ViewerPermissions & {
  comment_id: number
  post_id: number
  writer_employee_no: number
  writer_name: string | null
  parent_comment_id: number | null
  content: string
  created_at: string
  updated_at: string | null
}
