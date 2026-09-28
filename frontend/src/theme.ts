import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

export const equipmentPreset = definePreset(Aura, {
  primitive: { borderRadius: { md: '6px' } },
  semantic: {
    focusRing: { width: '2px', style: 'solid', color: '#337418', offset: '2px' },
    colorScheme: {
      light: {
        primary: {
          color: '#337418', contrastColor: '#f8f8f8',
          hoverColor: '#2b6214', activeColor: '#245210',
        },
        highlight: {
          background: '#eef4eb', focusBackground: '#eef4eb',
          color: '#337418', focusColor: '#245210',
        },
        text: { color: '#202020', mutedColor: '#606060' },
        formField: { borderColor: '#858585', focusBorderColor: '#337418' },
      },
    },
  },
})
