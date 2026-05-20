import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"

import { IconRail } from "./IconRail"

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <IconRail />
    </MemoryRouter>,
  )
}

describe("IconRail", () => {
  it("renders 5 nav links with correct aria-labels", () => {
    renderAt("/")

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeTruthy()
    expect(screen.getByRole("link", { name: "Cash transactions" })).toBeTruthy()
    expect(screen.getByRole("link", { name: "Sessions" })).toBeTruthy()
    expect(screen.getByRole("link", { name: "Stock" })).toBeTruthy()
    expect(screen.getByRole("link", { name: "Members" })).toBeTruthy()
  })

  it("marks the active link with aria-current=page", () => {
    renderAt("/cash")

    const cashLink = screen.getByRole("link", { name: "Cash transactions" })
    expect(cashLink.getAttribute("aria-current")).toBe("page")

    const dashLink = screen.getByRole("link", { name: "Dashboard" })
    expect(dashLink.getAttribute("aria-current")).toBeNull()
  })
})
