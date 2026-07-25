import { describe, it, expect, afterEach } from "vitest"
import { mount } from "@vue/test-utils"
import CommentComposer from "../../components/comments/CommentComposer.vue"
import type { Principal } from "../../services/comments"

const principals: Principal[] = [
  { id: 1, username: "alice" },
  { id: 2, username: "alice2" },
  { id: 3, username: "bob" },
]

let wrapper: any

afterEach(() => {
  wrapper?.unmount()
})

function mountComposer(props: Record<string, any> = {}) {
  wrapper = mount(CommentComposer, {
    props: { principals, ...props },
    attachTo: document.body,
  })
  return wrapper
}

describe("CommentComposer", () => {
  it("disables the submit button until there is non-whitespace text", async () => {
    mountComposer()
    const button = wrapper.find("button.composer-btn-primary")
    expect(button.attributes("disabled")).toBeDefined()

    await wrapper.find("textarea").setValue("   ")
    expect(wrapper.find("button.composer-btn-primary").attributes("disabled")).toBeDefined()

    await wrapper.find("textarea").setValue("hello")
    expect(wrapper.find("button.composer-btn-primary").attributes("disabled")).toBeUndefined()
  })

  it("emits submit with the trimmed body and clears the input", async () => {
    mountComposer()
    const textarea = wrapper.find("textarea")
    await textarea.setValue("  a great comment  ")
    await wrapper.find("button.composer-btn-primary").trigger("click")

    expect(wrapper.emitted("submit")).toEqual([["a great comment"]])
    expect((textarea.element as HTMLTextAreaElement).value).toBe("")
  })

  it("does not show the cancel button by default, and shows it when requested", () => {
    mountComposer()
    expect(wrapper.find("button.composer-btn-secondary").exists()).toBe(false)

    mountComposer({ showCancel: true })
    expect(wrapper.find("button.composer-btn-secondary").exists()).toBe(true)
  })

  it("emits cancel and clears the input", async () => {
    mountComposer({ showCancel: true })
    await wrapper.find("textarea").setValue("scratch text")
    await wrapper.find("button.composer-btn-secondary").trigger("click")

    expect(wrapper.emitted("cancel")).toHaveLength(1)
    expect((wrapper.find("textarea").element as HTMLTextAreaElement).value).toBe("")
  })

  it("pre-fills from initialBody, for editing an existing comment", () => {
    mountComposer({ initialBody: "original text" })
    expect((wrapper.find("textarea").element as HTMLTextAreaElement).value).toBe("original text")
  })

  it("shows @mention autocomplete filtered to the partial handle, and inserts the selection", async () => {
    mountComposer()
    const textarea = wrapper.find("textarea")
    const el = textarea.element as HTMLTextAreaElement

    await textarea.setValue("hey @ali")
    el.selectionStart = el.selectionEnd = el.value.length
    await textarea.trigger("keyup")

    const options = wrapper.findAll(".mention-option")
    expect(options).toHaveLength(2)
    expect(options[0].text()).toContain("alice")
    expect(options[1].text()).toContain("alice2")

    await options[0].trigger("mousedown")

    expect(el.value).toBe("hey @alice ")
  })

  it("hides the autocomplete once the mention is no longer active", async () => {
    mountComposer()
    const textarea = wrapper.find("textarea")
    const el = textarea.element as HTMLTextAreaElement

    await textarea.setValue("hey @al")
    el.selectionStart = el.selectionEnd = el.value.length
    await textarea.trigger("keyup")
    expect(wrapper.find(".mention-autocomplete").exists()).toBe(true)

    await textarea.setValue("hey @al ")
    el.selectionStart = el.selectionEnd = el.value.length
    await textarea.trigger("keyup")
    expect(wrapper.find(".mention-autocomplete").exists()).toBe(false)
  })

  it("submits on Cmd/Ctrl+Enter", async () => {
    mountComposer()
    await wrapper.find("textarea").setValue("quick submit")
    await wrapper.find("textarea").trigger("keydown", { key: "Enter", metaKey: true })

    expect(wrapper.emitted("submit")).toEqual([["quick submit"]])
  })
})
