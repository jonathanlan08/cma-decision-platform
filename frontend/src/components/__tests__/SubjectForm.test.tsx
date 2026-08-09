import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SubjectForm } from "../SubjectForm";

describe("SubjectForm", () => {
  it("blocks submission and shows an error when address is missing", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<SubjectForm onSave={onSave} />);

    await user.click(screen.getByRole("button", { name: /save subject property/i }));

    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/address is required/i);
    expect(screen.getByLabelText(/street address/i)).toHaveAttribute("aria-invalid", "true");
  });

  it("rejects a non-positive living area", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<SubjectForm onSave={onSave} />);

    await user.type(screen.getByLabelText(/street address/i), "12345 Demo Lane");
    await user.type(screen.getByLabelText(/living area/i), "-5");
    await user.click(screen.getByRole("button", { name: /save subject property/i }));

    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/greater than zero/i);
  });

  it("submits valid values", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<SubjectForm onSave={onSave} />);

    await user.type(screen.getByLabelText(/street address/i), "12345 Demo Lane");
    await user.type(screen.getByLabelText(/bedrooms/i), "3");
    await user.type(screen.getByLabelText(/living area/i), "1850");
    await user.click(screen.getByRole("button", { name: /save subject property/i }));

    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave.mock.calls[0][0]).toMatchObject({
      address: "12345 Demo Lane",
      bedrooms: 3,
      square_feet: 1850,
    });
  });

  it("prefills initial values", () => {
    render(
      <SubjectForm
        initial={{ address: "1 Existing Way", bedrooms: 4 }}
        onSave={vi.fn()}
      />,
    );
    expect(screen.getByLabelText(/street address/i)).toHaveValue("1 Existing Way");
    expect(screen.getByLabelText(/bedrooms/i)).toHaveValue(4);
  });
});
