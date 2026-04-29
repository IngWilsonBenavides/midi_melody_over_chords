/// <reference types="vite/client" />

// Extend JSX to include html-midi-player web components
declare namespace JSX {
  interface IntrinsicElements {
    "midi-player": React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
      src?: string;
      "sound-font"?: string;
      visualizer?: string;
      loop?: boolean;
    };
    "midi-visualizer": React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
      type?: "piano-roll" | "waterfall" | "staff";
      src?: string;
    };
  }
}
