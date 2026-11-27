/** Wraps an MDX component so its props are validated against the schema (if any) before it renders. */
import { defineComponent, h, type Component } from "vue"
import { MDX_COMPONENT_SCHEMAS } from "./mdxComponentSchemas"
import { validateProps } from "./mdxPropValidation"

export function withPropValidation(
  name: string,
  component: Component,
  extraProps: () => Record<string, unknown> = () => ({}),
): Component {
  const schema = MDX_COMPONENT_SCHEMAS[name]
  if (!schema) return component
  return defineComponent({
    name: `MdxValidated_${name}`,
    inheritAttrs: false,
    setup(_props, { attrs, slots }) {
      return () => {
        const result = validateProps(schema, attrs)
        if (!result.valid) {
          return h("div", { class: "mdx-invalid-props" }, [
            h("strong", `<${name}> has invalid props:`),
            h("ul", result.errors.map((e) => h("li", e))),
          ])
        }
        return h(component, { ...result.props, ...extraProps() }, slots)
      }
    },
  })
}
