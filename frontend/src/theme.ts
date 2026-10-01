import { definePreset } from "@primeuix/themes";
import Aura from "@primeuix/themes/aura";

export const equipmentPreset = definePreset(Aura, {
  primitive: { borderRadius: { md: "6px" } },
  semantic: {
    primary: {
      50: "#f1f8ed",
      100: "#dfefd6",
      200: "#c1dfb1",
      300: "#9bc980",
      400: "#70a84e",
      500: "#488b29",
      600: "#337418",
      700: "#2b6214",
      800: "#245210",
      900: "#1e420e",
      950: "#102607",
    },
    focusRing: {
      width: "2px",
      style: "solid",
      color: "#337418",
      offset: "2px",
    },
    colorScheme: {
      light: {
        primary: {
          color: "#337418",
          contrastColor: "#f8f8f8",
          hoverColor: "#2b6214",
          activeColor: "#245210",
        },
        highlight: {
          background: "#eef4eb",
          focusBackground: "#eef4eb",
          color: "#337418",
          focusColor: "#245210",
        },
        text: { color: "#202020", mutedColor: "#606060" },
        formField: { borderColor: "#858585", focusBorderColor: "#337418" },
      },
    },
  },
});
