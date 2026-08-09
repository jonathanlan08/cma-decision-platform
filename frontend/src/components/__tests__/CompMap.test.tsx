import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CompMap } from "../CompMap";
import { makeComparable } from "./fixtures";
import type { Subject } from "@/lib/types";

const subject: Subject = {
  address: "12345 Demo Lane",
  city: "Arcadia",
  zip_code: "91006",
  latitude: 34.134,
  longitude: -118.039,
  property_type: "single_family",
  bedrooms: 3,
  bathrooms: 2,
  square_feet: 1850,
  lot_size: 7200,
  year_built: 1958,
  condition: "good",
  parking_spaces: 2,
  has_pool: false,
  renovation_notes: null,
  agent_notes: null,
};

describe("CompMap", () => {
  it("asks for subject coordinates when they are missing", () => {
    render(
      <CompMap
        subject={{ ...subject, latitude: null, longitude: null }}
        comparables={[makeComparable({ latitude: 34.14, longitude: -118.03 })]}
      />,
    );
    expect(screen.getByText(/add latitude\/longitude to the subject/i)).toBeInTheDocument();
  });

  it("plots comparables with coordinates and counts the ones without", () => {
    const withCoords = makeComparable({ id: 1, latitude: 34.14, longitude: -118.03 });
    const withoutCoords = makeComparable({ id: 2, latitude: null, longitude: null });
    render(<CompMap subject={subject} comparables={[withCoords, withoutCoords]} />);

    const svg = screen.getByRole("img", { name: /proximity map: 1 comparable/i });
    expect(svg).toBeInTheDocument();
    expect(
      screen.getByText(/1 comparable\(s\) without coordinates not plotted/i),
    ).toBeInTheDocument();
  });

  it("shows an empty note when no comparable has coordinates", () => {
    render(
      <CompMap
        subject={subject}
        comparables={[makeComparable({ latitude: null, longitude: null })]}
      />,
    );
    expect(screen.getByText(/no comparables have coordinates/i)).toBeInTheDocument();
  });
});
