import { useRef, useState } from "react"
import type { FormEvent } from "react"

import { ApiError } from "../../../api/client"
import { createComment, deleteComment, updateComment } from "../../../api/board"
import { Alert, Button, ConfirmDialog, EmptyState, Textarea } from "../../../components/ui"
import type { Comment } from "../../../types/board"
import styles from "../board.module.css"
import { formatDateTime, writerLabel } from "../boardModel"

type Props = {
  postId: number
  comments: Comment[]
  enabled: boolean
  onChanged: () => Promise<void>
}

export function CommentThread({ postId, comments, enabled, onChanged }: Props) {
  const [draft, setDraft] = useState("")
  const [replyTarget, setReplyTarget] = useState<number | null>(null)
  const [replyDraft, setReplyDraft] = useState("")
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editDraft, setEditDraft] = useState("")
  const [deleteTarget, setDeleteTarget] = useState<Comment | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState("")
  const [fieldError, setFieldError] = useState("")
  const busy = useRef(false)

  async function run(task: () => Promise<unknown>, failure: string) {
    if (!enabled || busy.current) return false
    busy.current = true
    setSaving(true)
    setMessage("")
    setFieldError("")
    try {
      await task()
      await onChanged()
      return true
    } catch (caught) {
      if (caught instanceof ApiError) setFieldError(caught.fieldErrors.content?.[0] ?? "")
      setMessage(caught instanceof Error ? caught.message : failure)
      return false
    } finally {
      busy.current = false
      setSaving(false)
    }
  }

  async function submitComment(event: FormEvent) {
    event.preventDefault()
    if (!draft.trim()) return
    if (await run(() => createComment(postId, { content: draft }), "댓글을 작성하지 못했습니다.")) setDraft("")
  }

  async function submitReply(event: FormEvent, parentId: number) {
    event.preventDefault()
    if (!replyDraft.trim()) return
    if (await run(() => createComment(postId, { content: replyDraft, parent_comment_id: parentId }), "답글을 작성하지 못했습니다.")) {
      setReplyDraft("")
      setReplyTarget(null)
    }
  }

  async function submitEdit(event: FormEvent, commentId: number) {
    event.preventDefault()
    if (!editDraft.trim()) return
    if (await run(() => updateComment(commentId, editDraft), "댓글을 수정하지 못했습니다.")) setEditingId(null)
  }

  async function confirmDelete() {
    if (!deleteTarget) return
    if (await run(() => deleteComment(deleteTarget.comment_id), "댓글을 삭제하지 못했습니다.")) setDeleteTarget(null)
  }

  function startEdit(comment: Comment) {
    setEditingId(comment.comment_id)
    setEditDraft(comment.content)
    setReplyTarget(null)
  }

  function renderComment(comment: Comment, isReply: boolean) {
    const editing = editingId === comment.comment_id
    return <article key={comment.comment_id} className={`${styles.comment} ${isReply ? styles.reply : ""}`} aria-label={`${writerLabel(comment)}의 ${isReply ? "답글" : "댓글"}`}>
      <div className={styles.row}>
        <strong>{writerLabel(comment)}</strong>
        <span className={styles.muted}>{formatDateTime(comment.created_at)}{comment.updated_at ? " · 수정됨" : ""}</span>
      </div>
      {editing
        ? <form className={styles.stack} onSubmit={(event) => void submitEdit(event, comment.comment_id)}>
          <Textarea label="댓글 수정" rows={3} value={editDraft} error={fieldError || undefined} disabled={saving} onChange={(event) => setEditDraft(event.target.value)} />
          <div className={styles.row}>
            <Button type="submit" size="small" pending={saving} disabled={!editDraft.trim()}>저장</Button>
            <Button size="small" variant="secondary" disabled={saving} onClick={() => setEditingId(null)}>취소</Button>
          </div>
        </form>
        : <p className={styles.commentText}>{comment.content}</p>}
      {!editing && <div className={styles.row}>
        {!isReply && <Button size="small" variant="ghost" disabled={saving} aria-expanded={replyTarget === comment.comment_id} onClick={() => setReplyTarget(replyTarget === comment.comment_id ? null : comment.comment_id)}>답글</Button>}
        {comment.can_edit && <Button size="small" variant="ghost" disabled={saving} onClick={() => startEdit(comment)}>수정</Button>}
        {comment.can_delete && <Button size="small" variant="ghost" disabled={saving} onClick={() => setDeleteTarget(comment)}>삭제</Button>}
      </div>}
      {replyTarget === comment.comment_id && <form className={styles.stack} onSubmit={(event) => void submitReply(event, comment.comment_id)}>
        <Textarea label="답글" rows={2} value={replyDraft} disabled={saving} onChange={(event) => setReplyDraft(event.target.value)} />
        <div className={styles.row}><Button type="submit" size="small" pending={saving} disabled={!replyDraft.trim()}>답글 등록</Button></div>
      </form>}
    </article>
  }

  const topLevel = comments.filter((comment) => comment.parent_comment_id === null)
  return <section className={styles.stack} aria-labelledby="board-comments-heading">
    <h2 id="board-comments-heading">댓글 {comments.length}</h2>
    {message && <Alert tone="error">{message}</Alert>}
    <form className={styles.stack} onSubmit={(event) => void submitComment(event)}>
      <Textarea label="댓글 작성" rows={3} value={draft} disabled={saving || !enabled} error={editingId === null && replyTarget === null ? fieldError || undefined : undefined} onChange={(event) => setDraft(event.target.value)} />
      <div className={styles.row}><Button type="submit" pending={saving} disabled={!draft.trim() || !enabled}>댓글 등록</Button></div>
    </form>
    {topLevel.length === 0 && <EmptyState title="아직 댓글이 없습니다" />}
    {topLevel.map((comment) => <div key={comment.comment_id}>
      {renderComment(comment, false)}
      {comments.filter((reply) => reply.parent_comment_id === comment.comment_id).map((reply) => renderComment(reply, true))}
    </div>)}
    <ConfirmDialog open={deleteTarget !== null} title="댓글 삭제" danger confirmLabel="삭제" busy={saving} onClose={() => setDeleteTarget(null)} onConfirm={() => void confirmDelete()}>
      <p>이 댓글을 삭제할까요? 삭제한 댓글은 목록에 다시 표시되지 않습니다.</p>
    </ConfirmDialog>
  </section>
}
