import { useCallback, useEffect, useRef, useState } from "react"
import type { FormEvent } from "react"

import { ApiError } from "../../../api/client"
import { createPost, getEligibleNoticeCategories } from "../../../api/board"
import { Alert, Button, Card, EmptyState, ErrorState, Select, Spinner, Textarea, TextInput } from "../../../components/ui"
import type { NoticeCategory, PostType } from "../../../types/board"
import styles from "../board.module.css"
import { listHref, navigateTo, noticeCategoryLabels, postHref } from "../boardModel"

type FieldErrors = Record<string, string[]>
type LoadState = "loading" | "ready" | "error"

export function PostWriteScreen({ enabled }: { enabled: boolean }) {
  const [state, setState] = useState<LoadState>("loading")
  const [loadError, setLoadError] = useState("")
  const [eligible, setEligible] = useState<NoticeCategory[]>([])
  const [postType, setPostType] = useState<PostType>("일반")
  const [category, setCategory] = useState<NoticeCategory | "">("")
  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")
  const [errors, setErrors] = useState<FieldErrors>({})
  const [message, setMessage] = useState("")
  const [saving, setSaving] = useState(false)
  const generation = useRef(0)
  const busy = useRef(false)

  const load = useCallback(async () => {
    if (!enabled) return
    const run = ++generation.current
    setState("loading")
    try {
      const categories = await getEligibleNoticeCategories()
      if (run !== generation.current) return
      setEligible(categories)
      setCategory(categories[0] ?? "")
      setState("ready")
    } catch (caught) {
      if (run !== generation.current) return
      setLoadError(caught instanceof Error ? caught.message : "작성 화면을 불러오지 못했습니다.")
      setState("error")
    }
  }, [enabled])

  useEffect(() => {
    const counter = generation
    if (!enabled) return
    const timer = window.setTimeout(() => void load(), 0)
    return () => { counter.current++; window.clearTimeout(timer) }
  }, [enabled, load])

  const canWriteNotice = eligible.length > 0
  const writingNotice = canWriteNotice && postType === "공지"

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!enabled || busy.current) return
    busy.current = true
    setSaving(true)
    setErrors({})
    setMessage("")
    try {
      const saved = await createPost(writingNotice
        ? { post_type: "공지", notice_category: category || undefined, title, content }
        : { post_type: "일반", title, content })
      navigateTo(postHref(saved.post_id))
    } catch (caught) {
      if (caught instanceof ApiError) setErrors(caught.fieldErrors)
      setMessage(caught instanceof Error ? caught.message : "게시글을 등록하지 못했습니다.")
    } finally {
      busy.current = false
      setSaving(false)
    }
  }

  if (!enabled) return <EmptyState title="서버 연결 후 작성할 수 있습니다" />
  if (state === "loading") return <Spinner label="작성 화면을 준비하는 중" />
  if (state === "error") return <ErrorState onRetry={() => void load()}>{loadError}</ErrorState>

  return <Card title="게시글 작성" actions={<a className={styles.titleLink} href={listHref}>목록으로</a>}>
    <form className={styles.stack} onSubmit={submit} noValidate>
      {message && <Alert tone="error">{message}</Alert>}
      {canWriteNotice && <Select label="게시글 유형" value={postType} disabled={saving} onChange={(event) => setPostType(event.target.value as PostType)}>
        <option value="일반">일반글</option>
        <option value="공지">공지</option>
      </Select>}
      {writingNotice && <Select label="공지 분류" required value={category} error={errors.notice_category?.[0]} disabled={saving} onChange={(event) => setCategory(event.target.value as NoticeCategory)} hint="작성 권한이 있는 분류만 표시됩니다.">
        {eligible.map((code) => <option key={code} value={code}>{noticeCategoryLabels[code]}</option>)}
      </Select>}
      <TextInput label="제목" required maxLength={100} value={title} error={errors.title?.[0]} disabled={saving} onChange={(event) => setTitle(event.target.value)} hint="100자 이내" />
      <Textarea label="내용" required rows={10} value={content} error={errors.content?.[0]} disabled={saving} onChange={(event) => setContent(event.target.value)} />
      <div className={styles.row}>
        <Button type="submit" pending={saving} disabled={!title.trim() || !content.trim()}>등록</Button>
      </div>
    </form>
  </Card>
}
