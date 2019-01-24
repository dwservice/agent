/* Modified from the public domain program keysym2ucs.c,
 * as documented below.
 *
 * This module converts ISO 10646
 * (UCS, Unicode) values into X Keysym values.
 *
 * The array keysymtab[] contains pairs of X11 keysym values for graphical
 * characters and the corresponding Unicode value. The function
 * keysym2ucs() maps a Unicode value onto a keysym using a binary search,
 * therefore keysymtab[] must remain SORTED by ucs2 value.
 *
 * We allow to represent any UCS character in the range U-00000000 to
 * U-00FFFFFF by a keysym value in the range 0x01000000 to 0x01ffffff.
 * This admittedly does not cover the entire 31-bit space of UCS, but
 * it does cover all of the characters up to U-10FFFF, which can be
 * represented by UTF-16, and more, and it is very unlikely that higher
 * UCS codes will ever be assigned by ISO. So to get Unicode character
 * U+ABCD you can directly use keysym 0x0100abcd.
 *
 * NOTE: The comments in the table below contain the actual character
 * encoded in UTF-8, so for viewing and editing best use an editor in
 * UTF-8 mode.
 *
 * Author: Markus G. Kuhn <http://www.cl.cam.ac.uk/~mgk25/>,
 *         University of Cambridge, April 2001
 *
 * Special thanks to Richard Verhoeven <river@win.tue.nl> for preparing
 * an initial draft of the mapping table.
 *
 * This software is in the public domain. Share and enjoy!
 *
 */
#if defined OS_LINUX
#include <X11/X.h>

struct codepair {
  unsigned short keysym;
  unsigned short ucs;
} keysymtab[] = {
  { 0x0ba3, 0x003c }, /*                   leftcaret < LESS-THAN SIGN */
  { 0x0ba6, 0x003e }, /*                  rightcaret > GREATER-THAN SIGN */
  { 0x0bc6, 0x005f }, /*                    underbar _ LOW LINE */
  { 0x0bc0, 0x00af }, /*                     overbar Â¯ MACRON */

  { 0x01a1, 0x0104 }, /*                     Aogonek Ä„ LATIN CAPITAL LETTER A WITH OGONEK */
  { 0x01b1, 0x0105 }, /*                     aogonek Ä… LATIN SMALL LETTER A WITH OGONEK */
  { 0x01a5, 0x013d }, /*                      Lcaron Ä½ LATIN CAPITAL LETTER L WITH CARON */
  { 0x01a3, 0x0141 }, /*                     Lstroke Å� LATIN CAPITAL LETTER L WITH STROKE */
  { 0x01a6, 0x015a }, /*                      Sacute Åš LATIN CAPITAL LETTER S WITH ACUTE */
  { 0x01aa, 0x015e }, /*                    Scedilla Åž LATIN CAPITAL LETTER S WITH CEDILLA */
  { 0x01a9, 0x0160 }, /*                      Scaron Å  LATIN CAPITAL LETTER S WITH CARON */
  { 0x01ab, 0x0164 }, /*                      Tcaron Å¤ LATIN CAPITAL LETTER T WITH CARON */
  { 0x01ac, 0x0179 }, /*                      Zacute Å¹ LATIN CAPITAL LETTER Z WITH ACUTE */
  { 0x01af, 0x017b }, /*                   Zabovedot Å» LATIN CAPITAL LETTER Z WITH DOT ABOVE */
  { 0x01ae, 0x017d }, /*                      Zcaron Å½ LATIN CAPITAL LETTER Z WITH CARON */
  { 0x01b3, 0x0142 }, /*                     lstroke Å‚ LATIN SMALL LETTER L WITH STROKE */
  { 0x01b5, 0x013e }, /*                      lcaron Ä¾ LATIN SMALL LETTER L WITH CARON */
  { 0x01b6, 0x015b }, /*                      sacute Å› LATIN SMALL LETTER S WITH ACUTE */
  { 0x01b9, 0x0161 }, /*                      scaron Å¡ LATIN SMALL LETTER S WITH CARON */
  { 0x01ba, 0x015f }, /*                    scedilla ÅŸ LATIN SMALL LETTER S WITH CEDILLA */
  { 0x01bb, 0x0165 }, /*                      tcaron Å¥ LATIN SMALL LETTER T WITH CARON */
  { 0x01bc, 0x017a }, /*                      zacute Åº LATIN SMALL LETTER Z WITH ACUTE */
  { 0x01be, 0x017e }, /*                      zcaron Å¾ LATIN SMALL LETTER Z WITH CARON */
  { 0x01bf, 0x017c }, /*                   zabovedot Å¼ LATIN SMALL LETTER Z WITH DOT ABOVE */
  { 0x01c0, 0x0154 }, /*                      Racute Å” LATIN CAPITAL LETTER R WITH ACUTE */
  { 0x01c3, 0x0102 }, /*                      Abreve Ä‚ LATIN CAPITAL LETTER A WITH BREVE */
  { 0x01c5, 0x0139 }, /*                      Lacute Ä¹ LATIN CAPITAL LETTER L WITH ACUTE */
  { 0x01c6, 0x0106 }, /*                      Cacute Ä† LATIN CAPITAL LETTER C WITH ACUTE */
  { 0x01c8, 0x010c }, /*                      Ccaron ÄŒ LATIN CAPITAL LETTER C WITH CARON */
  { 0x01ca, 0x0118 }, /*                     Eogonek Ä˜ LATIN CAPITAL LETTER E WITH OGONEK */
  { 0x01cc, 0x011a }, /*                      Ecaron Äš LATIN CAPITAL LETTER E WITH CARON */
  { 0x01cf, 0x010e }, /*                      Dcaron ÄŽ LATIN CAPITAL LETTER D WITH CARON */
  { 0x01d0, 0x0110 }, /*                     Dstroke Ä� LATIN CAPITAL LETTER D WITH STROKE */
  { 0x01d1, 0x0143 }, /*                      Nacute Åƒ LATIN CAPITAL LETTER N WITH ACUTE */
  { 0x01d2, 0x0147 }, /*                      Ncaron Å‡ LATIN CAPITAL LETTER N WITH CARON */
  { 0x01d5, 0x0150 }, /*                Odoubleacute Å� LATIN CAPITAL LETTER O WITH DOUBLE ACUTE */
  { 0x01d8, 0x0158 }, /*                      Rcaron Å˜ LATIN CAPITAL LETTER R WITH CARON */
  { 0x01d9, 0x016e }, /*                       Uring Å® LATIN CAPITAL LETTER U WITH RING ABOVE */
  { 0x01db, 0x0170 }, /*                Udoubleacute Å° LATIN CAPITAL LETTER U WITH DOUBLE ACUTE */
  { 0x01de, 0x0162 }, /*                    Tcedilla Å¢ LATIN CAPITAL LETTER T WITH CEDILLA */
  { 0x01e0, 0x0155 }, /*                      racute Å• LATIN SMALL LETTER R WITH ACUTE */
  { 0x01e3, 0x0103 }, /*                      abreve Äƒ LATIN SMALL LETTER A WITH BREVE */
  { 0x01e5, 0x013a }, /*                      lacute Äº LATIN SMALL LETTER L WITH ACUTE */
  { 0x01e6, 0x0107 }, /*                      cacute Ä‡ LATIN SMALL LETTER C WITH ACUTE */
  { 0x01e8, 0x010d }, /*                      ccaron Ä� LATIN SMALL LETTER C WITH CARON */
  { 0x01ea, 0x0119 }, /*                     eogonek Ä™ LATIN SMALL LETTER E WITH OGONEK */
  { 0x01ec, 0x011b }, /*                      ecaron Ä› LATIN SMALL LETTER E WITH CARON */
  { 0x01ef, 0x010f }, /*                      dcaron Ä� LATIN SMALL LETTER D WITH CARON */
  { 0x01f0, 0x0111 }, /*                     dstroke Ä‘ LATIN SMALL LETTER D WITH STROKE */
  { 0x01f1, 0x0144 }, /*                      nacute Å„ LATIN SMALL LETTER N WITH ACUTE */
  { 0x01f2, 0x0148 }, /*                      ncaron Åˆ LATIN SMALL LETTER N WITH CARON */
  { 0x01f5, 0x0151 }, /*                odoubleacute Å‘ LATIN SMALL LETTER O WITH DOUBLE ACUTE */
  { 0x01f8, 0x0159 }, /*                      rcaron Å™ LATIN SMALL LETTER R WITH CARON */
  { 0x01f9, 0x016f }, /*                       uring Å¯ LATIN SMALL LETTER U WITH RING ABOVE */
  { 0x01fb, 0x0171 }, /*                udoubleacute Å± LATIN SMALL LETTER U WITH DOUBLE ACUTE */
  { 0x01fe, 0x0163 }, /*                    tcedilla Å£ LATIN SMALL LETTER T WITH CEDILLA */
  { 0x02a1, 0x0126 }, /*                     Hstroke Ä¦ LATIN CAPITAL LETTER H WITH STROKE */
  { 0x02a6, 0x0124 }, /*                 Hcircumflex Ä¤ LATIN CAPITAL LETTER H WITH CIRCUMFLEX */
  { 0x02a9, 0x0130 }, /*                   Iabovedot Ä° LATIN CAPITAL LETTER I WITH DOT ABOVE */
  { 0x02ab, 0x011e }, /*                      Gbreve Äž LATIN CAPITAL LETTER G WITH BREVE */
  { 0x02ac, 0x0134 }, /*                 Jcircumflex Ä´ LATIN CAPITAL LETTER J WITH CIRCUMFLEX */
  { 0x02b1, 0x0127 }, /*                     hstroke Ä§ LATIN SMALL LETTER H WITH STROKE */
  { 0x02b6, 0x0125 }, /*                 hcircumflex Ä¥ LATIN SMALL LETTER H WITH CIRCUMFLEX */
  { 0x02b9, 0x0131 }, /*                    idotless Ä± LATIN SMALL LETTER DOTLESS I */
  { 0x02bb, 0x011f }, /*                      gbreve ÄŸ LATIN SMALL LETTER G WITH BREVE */
  { 0x02bc, 0x0135 }, /*                 jcircumflex Äµ LATIN SMALL LETTER J WITH CIRCUMFLEX */
  { 0x02c5, 0x010a }, /*                   Cabovedot ÄŠ LATIN CAPITAL LETTER C WITH DOT ABOVE */
  { 0x02c6, 0x0108 }, /*                 Ccircumflex Äˆ LATIN CAPITAL LETTER C WITH CIRCUMFLEX */
  { 0x02d5, 0x0120 }, /*                   Gabovedot Ä  LATIN CAPITAL LETTER G WITH DOT ABOVE */
  { 0x02d8, 0x011c }, /*                 Gcircumflex Äœ LATIN CAPITAL LETTER G WITH CIRCUMFLEX */
  { 0x02dd, 0x016c }, /*                      Ubreve Å¬ LATIN CAPITAL LETTER U WITH BREVE */
  { 0x02de, 0x015c }, /*                 Scircumflex Åœ LATIN CAPITAL LETTER S WITH CIRCUMFLEX */
  { 0x02e5, 0x010b }, /*                   cabovedot Ä‹ LATIN SMALL LETTER C WITH DOT ABOVE */
  { 0x02e6, 0x0109 }, /*                 ccircumflex Ä‰ LATIN SMALL LETTER C WITH CIRCUMFLEX */
  { 0x02f5, 0x0121 }, /*                   gabovedot Ä¡ LATIN SMALL LETTER G WITH DOT ABOVE */
  { 0x02f8, 0x011d }, /*                 gcircumflex Ä� LATIN SMALL LETTER G WITH CIRCUMFLEX */
  { 0x02fd, 0x016d }, /*                      ubreve Å­ LATIN SMALL LETTER U WITH BREVE */
  { 0x02fe, 0x015d }, /*                 scircumflex Å� LATIN SMALL LETTER S WITH CIRCUMFLEX */
  { 0x03a2, 0x0138 }, /*                         kra Ä¸ LATIN SMALL LETTER KRA */
  { 0x03a3, 0x0156 }, /*                    Rcedilla Å– LATIN CAPITAL LETTER R WITH CEDILLA */
  { 0x03a5, 0x0128 }, /*                      Itilde Ä¨ LATIN CAPITAL LETTER I WITH TILDE */
  { 0x03a6, 0x013b }, /*                    Lcedilla Ä» LATIN CAPITAL LETTER L WITH CEDILLA */
  { 0x03aa, 0x0112 }, /*                     Emacron Ä’ LATIN CAPITAL LETTER E WITH MACRON */
  { 0x03ab, 0x0122 }, /*                    Gcedilla Ä¢ LATIN CAPITAL LETTER G WITH CEDILLA */
  { 0x03ac, 0x0166 }, /*                      Tslash Å¦ LATIN CAPITAL LETTER T WITH STROKE */
  { 0x03b3, 0x0157 }, /*                    rcedilla Å— LATIN SMALL LETTER R WITH CEDILLA */
  { 0x03b5, 0x0129 }, /*                      itilde Ä© LATIN SMALL LETTER I WITH TILDE */
  { 0x03b6, 0x013c }, /*                    lcedilla Ä¼ LATIN SMALL LETTER L WITH CEDILLA */
  { 0x03ba, 0x0113 }, /*                     emacron Ä“ LATIN SMALL LETTER E WITH MACRON */
  { 0x03bb, 0x0123 }, /*                    gcedilla Ä£ LATIN SMALL LETTER G WITH CEDILLA */
  { 0x03bc, 0x0167 }, /*                      tslash Å§ LATIN SMALL LETTER T WITH STROKE */
  { 0x03bd, 0x014a }, /*                         ENG ÅŠ LATIN CAPITAL LETTER ENG */
  { 0x03bf, 0x014b }, /*                         eng Å‹ LATIN SMALL LETTER ENG */
  { 0x03c0, 0x0100 }, /*                     Amacron Ä€ LATIN CAPITAL LETTER A WITH MACRON */
  { 0x03c7, 0x012e }, /*                     Iogonek Ä® LATIN CAPITAL LETTER I WITH OGONEK */
  { 0x03cc, 0x0116 }, /*                   Eabovedot Ä– LATIN CAPITAL LETTER E WITH DOT ABOVE */
  { 0x03cf, 0x012a }, /*                     Imacron Äª LATIN CAPITAL LETTER I WITH MACRON */
  { 0x03d1, 0x0145 }, /*                    Ncedilla Å… LATIN CAPITAL LETTER N WITH CEDILLA */
  { 0x03d2, 0x014c }, /*                     Omacron ÅŒ LATIN CAPITAL LETTER O WITH MACRON */
  { 0x03d3, 0x0136 }, /*                    Kcedilla Ä¶ LATIN CAPITAL LETTER K WITH CEDILLA */
  { 0x03d9, 0x0172 }, /*                     Uogonek Å² LATIN CAPITAL LETTER U WITH OGONEK */
  { 0x03dd, 0x0168 }, /*                      Utilde Å¨ LATIN CAPITAL LETTER U WITH TILDE */
  { 0x03de, 0x016a }, /*                     Umacron Åª LATIN CAPITAL LETTER U WITH MACRON */
  { 0x03e0, 0x0101 }, /*                     amacron Ä� LATIN SMALL LETTER A WITH MACRON */
  { 0x03e7, 0x012f }, /*                     iogonek Ä¯ LATIN SMALL LETTER I WITH OGONEK */
  { 0x03ec, 0x0117 }, /*                   eabovedot Ä— LATIN SMALL LETTER E WITH DOT ABOVE */
  { 0x03ef, 0x012b }, /*                     imacron Ä« LATIN SMALL LETTER I WITH MACRON */
  { 0x03f1, 0x0146 }, /*                    ncedilla Å† LATIN SMALL LETTER N WITH CEDILLA */
  { 0x03f2, 0x014d }, /*                     omacron Å� LATIN SMALL LETTER O WITH MACRON */
  { 0x03f3, 0x0137 }, /*                    kcedilla Ä· LATIN SMALL LETTER K WITH CEDILLA */
  { 0x03f9, 0x0173 }, /*                     uogonek Å³ LATIN SMALL LETTER U WITH OGONEK */
  { 0x03fd, 0x0169 }, /*                      utilde Å© LATIN SMALL LETTER U WITH TILDE */
  { 0x03fe, 0x016b }, /*                     umacron Å« LATIN SMALL LETTER U WITH MACRON */
  { 0x08f6, 0x0192 }, /*                    function Æ’ LATIN SMALL LETTER F WITH HOOK */
  { 0x13bc, 0x0152 }, /*                          OE Å’ LATIN CAPITAL LIGATURE OE */
  { 0x13bd, 0x0153 }, /*                          oe Å“ LATIN SMALL LIGATURE OE */
  { 0x13be, 0x0178 }, /*                  Ydiaeresis Å¸ LATIN CAPITAL LETTER Y WITH DIAERESIS */

  { 0x01b7, 0x02c7 }, /*                       caron Ë‡ CARON */
  { 0x01a2, 0x02d8 }, /*                       breve Ë˜ BREVE */
  { 0x01ff, 0x02d9 }, /*                    abovedot Ë™ DOT ABOVE */
  { 0x01b2, 0x02db }, /*                      ogonek Ë› OGONEK */
  { 0x01bd, 0x02dd }, /*                 doubleacute Ë� DOUBLE ACUTE ACCENT */

  { 0x07ae, 0x0385 }, /*        Greek_accentdieresis Î… GREEK DIALYTIKA TONOS */
  { 0x07a1, 0x0386 }, /*           Greek_ALPHAaccent Î† GREEK CAPITAL LETTER ALPHA WITH TONOS */
  { 0x07a2, 0x0388 }, /*         Greek_EPSILONaccent Îˆ GREEK CAPITAL LETTER EPSILON WITH TONOS */
  { 0x07a3, 0x0389 }, /*             Greek_ETAaccent Î‰ GREEK CAPITAL LETTER ETA WITH TONOS */
  { 0x07a4, 0x038a }, /*            Greek_IOTAaccent ÎŠ GREEK CAPITAL LETTER IOTA WITH TONOS */
  { 0x07a7, 0x038c }, /*         Greek_OMICRONaccent ÎŒ GREEK CAPITAL LETTER OMICRON WITH TONOS */
  { 0x07a8, 0x038e }, /*         Greek_UPSILONaccent ÎŽ GREEK CAPITAL LETTER UPSILON WITH TONOS */
  { 0x07ab, 0x038f }, /*           Greek_OMEGAaccent Î� GREEK CAPITAL LETTER OMEGA WITH TONOS */
  { 0x07b6, 0x0390 }, /*    Greek_iotaaccentdieresis Î� GREEK SMALL LETTER IOTA WITH DIALYTIKA AND TONOS */
  { 0x07c1, 0x0391 }, /*                 Greek_ALPHA Î‘ GREEK CAPITAL LETTER ALPHA */
  { 0x07c2, 0x0392 }, /*                  Greek_BETA Î’ GREEK CAPITAL LETTER BETA */
  { 0x07c3, 0x0393 }, /*                 Greek_GAMMA Î“ GREEK CAPITAL LETTER GAMMA */
  { 0x07c4, 0x0394 }, /*                 Greek_DELTA Î” GREEK CAPITAL LETTER DELTA */
  { 0x07c5, 0x0395 }, /*               Greek_EPSILON Î• GREEK CAPITAL LETTER EPSILON */
  { 0x07c6, 0x0396 }, /*                  Greek_ZETA Î– GREEK CAPITAL LETTER ZETA */
  { 0x07c7, 0x0397 }, /*                   Greek_ETA Î— GREEK CAPITAL LETTER ETA */
  { 0x07c8, 0x0398 }, /*                 Greek_THETA Î˜ GREEK CAPITAL LETTER THETA */
  { 0x07c9, 0x0399 }, /*                  Greek_IOTA Î™ GREEK CAPITAL LETTER IOTA */
  { 0x07ca, 0x039a }, /*                 Greek_KAPPA Îš GREEK CAPITAL LETTER KAPPA */
  { 0x07cb, 0x039b }, /*                Greek_LAMBDA Î› GREEK CAPITAL LETTER LAMDA */
  { 0x07cc, 0x039c }, /*                    Greek_MU Îœ GREEK CAPITAL LETTER MU */
  { 0x07cd, 0x039d }, /*                    Greek_NU Î� GREEK CAPITAL LETTER NU */
  { 0x07ce, 0x039e }, /*                    Greek_XI Îž GREEK CAPITAL LETTER XI */
  { 0x07cf, 0x039f }, /*               Greek_OMICRON ÎŸ GREEK CAPITAL LETTER OMICRON */
  { 0x07d0, 0x03a0 }, /*                    Greek_PI Î  GREEK CAPITAL LETTER PI */
  { 0x07d1, 0x03a1 }, /*                   Greek_RHO Î¡ GREEK CAPITAL LETTER RHO */
  { 0x07d2, 0x03a3 }, /*                 Greek_SIGMA Î£ GREEK CAPITAL LETTER SIGMA */
  { 0x07d4, 0x03a4 }, /*                   Greek_TAU Î¤ GREEK CAPITAL LETTER TAU */
  { 0x07d5, 0x03a5 }, /*               Greek_UPSILON Î¥ GREEK CAPITAL LETTER UPSILON */
  { 0x07d6, 0x03a6 }, /*                   Greek_PHI Î¦ GREEK CAPITAL LETTER PHI */
  { 0x07d7, 0x03a7 }, /*                   Greek_CHI Î§ GREEK CAPITAL LETTER CHI */
  { 0x07d8, 0x03a8 }, /*                   Greek_PSI Î¨ GREEK CAPITAL LETTER PSI */
  { 0x07d9, 0x03a9 }, /*                 Greek_OMEGA Î© GREEK CAPITAL LETTER OMEGA */
  { 0x07a5, 0x03aa }, /*         Greek_IOTAdiaeresis Îª GREEK CAPITAL LETTER IOTA WITH DIALYTIKA */
  { 0x07a9, 0x03ab }, /*       Greek_UPSILONdieresis Î« GREEK CAPITAL LETTER UPSILON WITH DIALYTIKA */
  { 0x07b1, 0x03ac }, /*           Greek_alphaaccent Î¬ GREEK SMALL LETTER ALPHA WITH TONOS */
  { 0x07b2, 0x03ad }, /*         Greek_epsilonaccent Î­ GREEK SMALL LETTER EPSILON WITH TONOS */
  { 0x07b3, 0x03ae }, /*             Greek_etaaccent Î® GREEK SMALL LETTER ETA WITH TONOS */
  { 0x07b4, 0x03af }, /*            Greek_iotaaccent Î¯ GREEK SMALL LETTER IOTA WITH TONOS */
  { 0x07ba, 0x03b0 }, /* Greek_upsilonaccentdieresis Î° GREEK SMALL LETTER UPSILON WITH DIALYTIKA AND TONOS */
  { 0x07e1, 0x03b1 }, /*                 Greek_alpha Î± GREEK SMALL LETTER ALPHA */
  { 0x07e2, 0x03b2 }, /*                  Greek_beta Î² GREEK SMALL LETTER BETA */
  { 0x07e3, 0x03b3 }, /*                 Greek_gamma Î³ GREEK SMALL LETTER GAMMA */
  { 0x07e4, 0x03b4 }, /*                 Greek_delta Î´ GREEK SMALL LETTER DELTA */
  { 0x07e5, 0x03b5 }, /*               Greek_epsilon Îµ GREEK SMALL LETTER EPSILON */
  { 0x07e6, 0x03b6 }, /*                  Greek_zeta Î¶ GREEK SMALL LETTER ZETA */
  { 0x07e7, 0x03b7 }, /*                   Greek_eta Î· GREEK SMALL LETTER ETA */
  { 0x07e8, 0x03b8 }, /*                 Greek_theta Î¸ GREEK SMALL LETTER THETA */
  { 0x07e9, 0x03b9 }, /*                  Greek_iota Î¹ GREEK SMALL LETTER IOTA */
  { 0x07ea, 0x03ba }, /*                 Greek_kappa Îº GREEK SMALL LETTER KAPPA */
  { 0x07eb, 0x03bb }, /*                Greek_lambda Î» GREEK SMALL LETTER LAMDA */
  { 0x07ec, 0x03bc }, /*                    Greek_mu Î¼ GREEK SMALL LETTER MU */
  { 0x07ed, 0x03bd }, /*                    Greek_nu Î½ GREEK SMALL LETTER NU */
  { 0x07ee, 0x03be }, /*                    Greek_xi Î¾ GREEK SMALL LETTER XI */
  { 0x07ef, 0x03bf }, /*               Greek_omicron Î¿ GREEK SMALL LETTER OMICRON */
  { 0x07f0, 0x03c0 }, /*                    Greek_pi Ï€ GREEK SMALL LETTER PI */
  { 0x07f1, 0x03c1 }, /*                   Greek_rho Ï� GREEK SMALL LETTER RHO */
  { 0x07f3, 0x03c2 }, /*       Greek_finalsmallsigma Ï‚ GREEK SMALL LETTER FINAL SIGMA */
  { 0x07f2, 0x03c3 }, /*                 Greek_sigma Ïƒ GREEK SMALL LETTER SIGMA */
  { 0x07f4, 0x03c4 }, /*                   Greek_tau Ï„ GREEK SMALL LETTER TAU */
  { 0x07f5, 0x03c5 }, /*               Greek_upsilon Ï… GREEK SMALL LETTER UPSILON */
  { 0x07f6, 0x03c6 }, /*                   Greek_phi Ï† GREEK SMALL LETTER PHI */
  { 0x07f7, 0x03c7 }, /*                   Greek_chi Ï‡ GREEK SMALL LETTER CHI */
  { 0x07f8, 0x03c8 }, /*                   Greek_psi Ïˆ GREEK SMALL LETTER PSI */
  { 0x07f9, 0x03c9 }, /*                 Greek_omega Ï‰ GREEK SMALL LETTER OMEGA */
  { 0x07b5, 0x03ca }, /*          Greek_iotadieresis ÏŠ GREEK SMALL LETTER IOTA WITH DIALYTIKA */
  { 0x07b9, 0x03cb }, /*       Greek_upsilondieresis Ï‹ GREEK SMALL LETTER UPSILON WITH DIALYTIKA */
  { 0x07b7, 0x03cc }, /*         Greek_omicronaccent ÏŒ GREEK SMALL LETTER OMICRON WITH TONOS */
  { 0x07b8, 0x03cd }, /*         Greek_upsilonaccent Ï� GREEK SMALL LETTER UPSILON WITH TONOS */
  { 0x07bb, 0x03ce }, /*           Greek_omegaaccent ÏŽ GREEK SMALL LETTER OMEGA WITH TONOS */

  { 0x06b3, 0x0401 }, /*                 Cyrillic_IO Ð� CYRILLIC CAPITAL LETTER IO */
  { 0x06b1, 0x0402 }, /*                 Serbian_DJE Ð‚ CYRILLIC CAPITAL LETTER DJE */
  { 0x06b2, 0x0403 }, /*               Macedonia_GJE Ðƒ CYRILLIC CAPITAL LETTER GJE */
  { 0x06b4, 0x0404 }, /*                Ukrainian_IE Ð„ CYRILLIC CAPITAL LETTER UKRAINIAN IE */
  { 0x06b5, 0x0405 }, /*               Macedonia_DSE Ð… CYRILLIC CAPITAL LETTER DZE */
  { 0x06b6, 0x0406 }, /*                 Ukrainian_I Ð† CYRILLIC CAPITAL LETTER BYELORUSSIAN-UKRAINIAN I */
  { 0x06b7, 0x0407 }, /*                Ukrainian_YI Ð‡ CYRILLIC CAPITAL LETTER YI */
  { 0x06b8, 0x0408 }, /*                 Cyrillic_JE Ðˆ CYRILLIC CAPITAL LETTER JE */
  { 0x06b9, 0x0409 }, /*                Cyrillic_LJE Ð‰ CYRILLIC CAPITAL LETTER LJE */
  { 0x06ba, 0x040a }, /*                Cyrillic_NJE ÐŠ CYRILLIC CAPITAL LETTER NJE */
  { 0x06bb, 0x040b }, /*                Serbian_TSHE Ð‹ CYRILLIC CAPITAL LETTER TSHE */
  { 0x06bc, 0x040c }, /*               Macedonia_KJE ÐŒ CYRILLIC CAPITAL LETTER KJE */
  { 0x06be, 0x040e }, /*         Byelorussian_SHORTU ÐŽ CYRILLIC CAPITAL LETTER SHORT U */
  { 0x06bf, 0x040f }, /*               Cyrillic_DZHE Ð� CYRILLIC CAPITAL LETTER DZHE */
  { 0x06e1, 0x0410 }, /*                  Cyrillic_A Ð� CYRILLIC CAPITAL LETTER A */
  { 0x06e2, 0x0411 }, /*                 Cyrillic_BE Ð‘ CYRILLIC CAPITAL LETTER BE */
  { 0x06f7, 0x0412 }, /*                 Cyrillic_VE Ð’ CYRILLIC CAPITAL LETTER VE */
  { 0x06e7, 0x0413 }, /*                Cyrillic_GHE Ð“ CYRILLIC CAPITAL LETTER GHE */
  { 0x06e4, 0x0414 }, /*                 Cyrillic_DE Ð” CYRILLIC CAPITAL LETTER DE */
  { 0x06e5, 0x0415 }, /*                 Cyrillic_IE Ð• CYRILLIC CAPITAL LETTER IE */
  { 0x06f6, 0x0416 }, /*                Cyrillic_ZHE Ð– CYRILLIC CAPITAL LETTER ZHE */
  { 0x06fa, 0x0417 }, /*                 Cyrillic_ZE Ð— CYRILLIC CAPITAL LETTER ZE */
  { 0x06e9, 0x0418 }, /*                  Cyrillic_I Ð˜ CYRILLIC CAPITAL LETTER I */
  { 0x06ea, 0x0419 }, /*             Cyrillic_SHORTI Ð™ CYRILLIC CAPITAL LETTER SHORT I */
  { 0x06eb, 0x041a }, /*                 Cyrillic_KA Ðš CYRILLIC CAPITAL LETTER KA */
  { 0x06ec, 0x041b }, /*                 Cyrillic_EL Ð› CYRILLIC CAPITAL LETTER EL */
  { 0x06ed, 0x041c }, /*                 Cyrillic_EM Ðœ CYRILLIC CAPITAL LETTER EM */
  { 0x06ee, 0x041d }, /*                 Cyrillic_EN Ð� CYRILLIC CAPITAL LETTER EN */
  { 0x06ef, 0x041e }, /*                  Cyrillic_O Ðž CYRILLIC CAPITAL LETTER O */
  { 0x06f0, 0x041f }, /*                 Cyrillic_PE ÐŸ CYRILLIC CAPITAL LETTER PE */
  { 0x06f2, 0x0420 }, /*                 Cyrillic_ER Ð  CYRILLIC CAPITAL LETTER ER */
  { 0x06f3, 0x0421 }, /*                 Cyrillic_ES Ð¡ CYRILLIC CAPITAL LETTER ES */
  { 0x06f4, 0x0422 }, /*                 Cyrillic_TE Ð¢ CYRILLIC CAPITAL LETTER TE */
  { 0x06f5, 0x0423 }, /*                  Cyrillic_U Ð£ CYRILLIC CAPITAL LETTER U */
  { 0x06e6, 0x0424 }, /*                 Cyrillic_EF Ð¤ CYRILLIC CAPITAL LETTER EF */
  { 0x06e8, 0x0425 }, /*                 Cyrillic_HA Ð¥ CYRILLIC CAPITAL LETTER HA */
  { 0x06e3, 0x0426 }, /*                Cyrillic_TSE Ð¦ CYRILLIC CAPITAL LETTER TSE */
  { 0x06fe, 0x0427 }, /*                Cyrillic_CHE Ð§ CYRILLIC CAPITAL LETTER CHE */
  { 0x06fb, 0x0428 }, /*                Cyrillic_SHA Ð¨ CYRILLIC CAPITAL LETTER SHA */
  { 0x06fd, 0x0429 }, /*              Cyrillic_SHCHA Ð© CYRILLIC CAPITAL LETTER SHCHA */
  { 0x06ff, 0x042a }, /*           Cyrillic_HARDSIGN Ðª CYRILLIC CAPITAL LETTER HARD SIGN */
  { 0x06f9, 0x042b }, /*               Cyrillic_YERU Ð« CYRILLIC CAPITAL LETTER YERU */
  { 0x06f8, 0x042c }, /*           Cyrillic_SOFTSIGN Ð¬ CYRILLIC CAPITAL LETTER SOFT SIGN */
  { 0x06fc, 0x042d }, /*                  Cyrillic_E Ð­ CYRILLIC CAPITAL LETTER E */
  { 0x06e0, 0x042e }, /*                 Cyrillic_YU Ð® CYRILLIC CAPITAL LETTER YU */
  { 0x06f1, 0x042f }, /*                 Cyrillic_YA Ð¯ CYRILLIC CAPITAL LETTER YA */
  { 0x06c1, 0x0430 }, /*                  Cyrillic_a Ð° CYRILLIC SMALL LETTER A */
  { 0x06c2, 0x0431 }, /*                 Cyrillic_be Ð± CYRILLIC SMALL LETTER BE */
  { 0x06d7, 0x0432 }, /*                 Cyrillic_ve Ð² CYRILLIC SMALL LETTER VE */
  { 0x06c7, 0x0433 }, /*                Cyrillic_ghe Ð³ CYRILLIC SMALL LETTER GHE */
  { 0x06c4, 0x0434 }, /*                 Cyrillic_de Ð´ CYRILLIC SMALL LETTER DE */
  { 0x06c5, 0x0435 }, /*                 Cyrillic_ie Ðµ CYRILLIC SMALL LETTER IE */
  { 0x06d6, 0x0436 }, /*                Cyrillic_zhe Ð¶ CYRILLIC SMALL LETTER ZHE */
  { 0x06da, 0x0437 }, /*                 Cyrillic_ze Ð· CYRILLIC SMALL LETTER ZE */
  { 0x06c9, 0x0438 }, /*                  Cyrillic_i Ð¸ CYRILLIC SMALL LETTER I */
  { 0x06ca, 0x0439 }, /*             Cyrillic_shorti Ð¹ CYRILLIC SMALL LETTER SHORT I */
  { 0x06cb, 0x043a }, /*                 Cyrillic_ka Ðº CYRILLIC SMALL LETTER KA */
  { 0x06cc, 0x043b }, /*                 Cyrillic_el Ð» CYRILLIC SMALL LETTER EL */
  { 0x06cd, 0x043c }, /*                 Cyrillic_em Ð¼ CYRILLIC SMALL LETTER EM */
  { 0x06ce, 0x043d }, /*                 Cyrillic_en Ð½ CYRILLIC SMALL LETTER EN */
  { 0x06cf, 0x043e }, /*                  Cyrillic_o Ð¾ CYRILLIC SMALL LETTER O */
  { 0x06d0, 0x043f }, /*                 Cyrillic_pe Ð¿ CYRILLIC SMALL LETTER PE */
  { 0x06d2, 0x0440 }, /*                 Cyrillic_er Ñ€ CYRILLIC SMALL LETTER ER */
  { 0x06d3, 0x0441 }, /*                 Cyrillic_es Ñ� CYRILLIC SMALL LETTER ES */
  { 0x06d4, 0x0442 }, /*                 Cyrillic_te Ñ‚ CYRILLIC SMALL LETTER TE */
  { 0x06d5, 0x0443 }, /*                  Cyrillic_u Ñƒ CYRILLIC SMALL LETTER U */
  { 0x06c6, 0x0444 }, /*                 Cyrillic_ef Ñ„ CYRILLIC SMALL LETTER EF */
  { 0x06c8, 0x0445 }, /*                 Cyrillic_ha Ñ… CYRILLIC SMALL LETTER HA */
  { 0x06c3, 0x0446 }, /*                Cyrillic_tse Ñ† CYRILLIC SMALL LETTER TSE */
  { 0x06de, 0x0447 }, /*                Cyrillic_che Ñ‡ CYRILLIC SMALL LETTER CHE */
  { 0x06db, 0x0448 }, /*                Cyrillic_sha Ñˆ CYRILLIC SMALL LETTER SHA */
  { 0x06dd, 0x0449 }, /*              Cyrillic_shcha Ñ‰ CYRILLIC SMALL LETTER SHCHA */
  { 0x06df, 0x044a }, /*           Cyrillic_hardsign ÑŠ CYRILLIC SMALL LETTER HARD SIGN */
  { 0x06d9, 0x044b }, /*               Cyrillic_yeru Ñ‹ CYRILLIC SMALL LETTER YERU */
  { 0x06d8, 0x044c }, /*           Cyrillic_softsign ÑŒ CYRILLIC SMALL LETTER SOFT SIGN */
  { 0x06dc, 0x044d }, /*                  Cyrillic_e Ñ� CYRILLIC SMALL LETTER E */
  { 0x06c0, 0x044e }, /*                 Cyrillic_yu ÑŽ CYRILLIC SMALL LETTER YU */
  { 0x06d1, 0x044f }, /*                 Cyrillic_ya Ñ� CYRILLIC SMALL LETTER YA */
  { 0x06a3, 0x0451 }, /*                 Cyrillic_io Ñ‘ CYRILLIC SMALL LETTER IO */
  { 0x06a1, 0x0452 }, /*                 Serbian_dje Ñ’ CYRILLIC SMALL LETTER DJE */
  { 0x06a2, 0x0453 }, /*               Macedonia_gje Ñ“ CYRILLIC SMALL LETTER GJE */
  { 0x06a4, 0x0454 }, /*                Ukrainian_ie Ñ” CYRILLIC SMALL LETTER UKRAINIAN IE */
  { 0x06a5, 0x0455 }, /*               Macedonia_dse Ñ• CYRILLIC SMALL LETTER DZE */
  { 0x06a6, 0x0456 }, /*                 Ukrainian_i Ñ– CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I */
  { 0x06a7, 0x0457 }, /*                Ukrainian_yi Ñ— CYRILLIC SMALL LETTER YI */
  { 0x06a8, 0x0458 }, /*                 Cyrillic_je Ñ˜ CYRILLIC SMALL LETTER JE */
  { 0x06a9, 0x0459 }, /*                Cyrillic_lje Ñ™ CYRILLIC SMALL LETTER LJE */
  { 0x06aa, 0x045a }, /*                Cyrillic_nje Ñš CYRILLIC SMALL LETTER NJE */
  { 0x06ab, 0x045b }, /*                Serbian_tshe Ñ› CYRILLIC SMALL LETTER TSHE */
  { 0x06ac, 0x045c }, /*               Macedonia_kje Ñœ CYRILLIC SMALL LETTER KJE */
  { 0x06ae, 0x045e }, /*         Byelorussian_shortu Ñž CYRILLIC SMALL LETTER SHORT U */
  { 0x06af, 0x045f }, /*               Cyrillic_dzhe ÑŸ CYRILLIC SMALL LETTER DZHE */

  { 0x0ce0, 0x05d0 }, /*                hebrew_aleph ×� HEBREW LETTER ALEF */
  { 0x0ce1, 0x05d1 }, /*                  hebrew_bet ×‘ HEBREW LETTER BET */
  { 0x0ce2, 0x05d2 }, /*                hebrew_gimel ×’ HEBREW LETTER GIMEL */
  { 0x0ce3, 0x05d3 }, /*                hebrew_dalet ×“ HEBREW LETTER DALET */
  { 0x0ce4, 0x05d4 }, /*                   hebrew_he ×” HEBREW LETTER HE */
  { 0x0ce5, 0x05d5 }, /*                  hebrew_waw ×• HEBREW LETTER VAV */
  { 0x0ce6, 0x05d6 }, /*                 hebrew_zain ×– HEBREW LETTER ZAYIN */
  { 0x0ce7, 0x05d7 }, /*                 hebrew_chet ×— HEBREW LETTER HET */
  { 0x0ce8, 0x05d8 }, /*                  hebrew_tet ×˜ HEBREW LETTER TET */
  { 0x0ce9, 0x05d9 }, /*                  hebrew_yod ×™ HEBREW LETTER YOD */
  { 0x0cea, 0x05da }, /*            hebrew_finalkaph ×š HEBREW LETTER FINAL KAF */
  { 0x0ceb, 0x05db }, /*                 hebrew_kaph ×› HEBREW LETTER KAF */
  { 0x0cec, 0x05dc }, /*                hebrew_lamed ×œ HEBREW LETTER LAMED */
  { 0x0ced, 0x05dd }, /*             hebrew_finalmem ×� HEBREW LETTER FINAL MEM */
  { 0x0cee, 0x05de }, /*                  hebrew_mem ×ž HEBREW LETTER MEM */
  { 0x0cef, 0x05df }, /*             hebrew_finalnun ×Ÿ HEBREW LETTER FINAL NUN */
  { 0x0cf0, 0x05e0 }, /*                  hebrew_nun ×  HEBREW LETTER NUN */
  { 0x0cf1, 0x05e1 }, /*               hebrew_samech ×¡ HEBREW LETTER SAMEKH */
  { 0x0cf2, 0x05e2 }, /*                 hebrew_ayin ×¢ HEBREW LETTER AYIN */
  { 0x0cf3, 0x05e3 }, /*              hebrew_finalpe ×£ HEBREW LETTER FINAL PE */
  { 0x0cf4, 0x05e4 }, /*                   hebrew_pe ×¤ HEBREW LETTER PE */
  { 0x0cf5, 0x05e5 }, /*            hebrew_finalzade ×¥ HEBREW LETTER FINAL TSADI */
  { 0x0cf6, 0x05e6 }, /*                 hebrew_zade ×¦ HEBREW LETTER TSADI */
  { 0x0cf7, 0x05e7 }, /*                 hebrew_qoph ×§ HEBREW LETTER QOF */
  { 0x0cf8, 0x05e8 }, /*                 hebrew_resh ×¨ HEBREW LETTER RESH */
  { 0x0cf9, 0x05e9 }, /*                 hebrew_shin ×© HEBREW LETTER SHIN */
  { 0x0cfa, 0x05ea }, /*                  hebrew_taw ×ª HEBREW LETTER TAV */

  { 0x05ac, 0x060c }, /*                Arabic_comma ØŒ ARABIC COMMA */
  { 0x05bb, 0x061b }, /*            Arabic_semicolon Ø› ARABIC SEMICOLON */
  { 0x05bf, 0x061f }, /*        Arabic_question_mark ØŸ ARABIC QUESTION MARK */
  { 0x05c1, 0x0621 }, /*                Arabic_hamza Ø¡ ARABIC LETTER HAMZA */
  { 0x05c2, 0x0622 }, /*          Arabic_maddaonalef Ø¢ ARABIC LETTER ALEF WITH MADDA ABOVE */
  { 0x05c3, 0x0623 }, /*          Arabic_hamzaonalef Ø£ ARABIC LETTER ALEF WITH HAMZA ABOVE */
  { 0x05c4, 0x0624 }, /*           Arabic_hamzaonwaw Ø¤ ARABIC LETTER WAW WITH HAMZA ABOVE */
  { 0x05c5, 0x0625 }, /*       Arabic_hamzaunderalef Ø¥ ARABIC LETTER ALEF WITH HAMZA BELOW */
  { 0x05c6, 0x0626 }, /*           Arabic_hamzaonyeh Ø¦ ARABIC LETTER YEH WITH HAMZA ABOVE */
  { 0x05c7, 0x0627 }, /*                 Arabic_alef Ø§ ARABIC LETTER ALEF */
  { 0x05c8, 0x0628 }, /*                  Arabic_beh Ø¨ ARABIC LETTER BEH */
  { 0x05c9, 0x0629 }, /*           Arabic_tehmarbuta Ø© ARABIC LETTER TEH MARBUTA */
  { 0x05ca, 0x062a }, /*                  Arabic_teh Øª ARABIC LETTER TEH */
  { 0x05cb, 0x062b }, /*                 Arabic_theh Ø« ARABIC LETTER THEH */
  { 0x05cc, 0x062c }, /*                 Arabic_jeem Ø¬ ARABIC LETTER JEEM */
  { 0x05cd, 0x062d }, /*                  Arabic_hah Ø­ ARABIC LETTER HAH */
  { 0x05ce, 0x062e }, /*                 Arabic_khah Ø® ARABIC LETTER KHAH */
  { 0x05cf, 0x062f }, /*                  Arabic_dal Ø¯ ARABIC LETTER DAL */
  { 0x05d0, 0x0630 }, /*                 Arabic_thal Ø° ARABIC LETTER THAL */
  { 0x05d1, 0x0631 }, /*                   Arabic_ra Ø± ARABIC LETTER REH */
  { 0x05d2, 0x0632 }, /*                 Arabic_zain Ø² ARABIC LETTER ZAIN */
  { 0x05d3, 0x0633 }, /*                 Arabic_seen Ø³ ARABIC LETTER SEEN */
  { 0x05d4, 0x0634 }, /*                Arabic_sheen Ø´ ARABIC LETTER SHEEN */
  { 0x05d5, 0x0635 }, /*                  Arabic_sad Øµ ARABIC LETTER SAD */
  { 0x05d6, 0x0636 }, /*                  Arabic_dad Ø¶ ARABIC LETTER DAD */
  { 0x05d7, 0x0637 }, /*                  Arabic_tah Ø· ARABIC LETTER TAH */
  { 0x05d8, 0x0638 }, /*                  Arabic_zah Ø¸ ARABIC LETTER ZAH */
  { 0x05d9, 0x0639 }, /*                  Arabic_ain Ø¹ ARABIC LETTER AIN */
  { 0x05da, 0x063a }, /*                Arabic_ghain Øº ARABIC LETTER GHAIN */
  { 0x05e0, 0x0640 }, /*              Arabic_tatweel Ù€ ARABIC TATWEEL */
  { 0x05e1, 0x0641 }, /*                  Arabic_feh Ù� ARABIC LETTER FEH */
  { 0x05e2, 0x0642 }, /*                  Arabic_qaf Ù‚ ARABIC LETTER QAF */
  { 0x05e3, 0x0643 }, /*                  Arabic_kaf Ùƒ ARABIC LETTER KAF */
  { 0x05e4, 0x0644 }, /*                  Arabic_lam Ù„ ARABIC LETTER LAM */
  { 0x05e5, 0x0645 }, /*                 Arabic_meem Ù… ARABIC LETTER MEEM */
  { 0x05e6, 0x0646 }, /*                 Arabic_noon Ù† ARABIC LETTER NOON */
  { 0x05e7, 0x0647 }, /*                   Arabic_ha Ù‡ ARABIC LETTER HEH */
  { 0x05e8, 0x0648 }, /*                  Arabic_waw Ùˆ ARABIC LETTER WAW */
  { 0x05e9, 0x0649 }, /*          Arabic_alefmaksura Ù‰ ARABIC LETTER ALEF MAKSURA */
  { 0x05ea, 0x064a }, /*                  Arabic_yeh ÙŠ ARABIC LETTER YEH */
  { 0x05eb, 0x064b }, /*             Arabic_fathatan Ù‹ ARABIC FATHATAN */
  { 0x05ec, 0x064c }, /*             Arabic_dammatan ÙŒ ARABIC DAMMATAN */
  { 0x05ed, 0x064d }, /*             Arabic_kasratan Ù� ARABIC KASRATAN */
  { 0x05ee, 0x064e }, /*                Arabic_fatha ÙŽ ARABIC FATHA */
  { 0x05ef, 0x064f }, /*                Arabic_damma Ù� ARABIC DAMMA */
  { 0x05f0, 0x0650 }, /*                Arabic_kasra Ù� ARABIC KASRA */
  { 0x05f1, 0x0651 }, /*               Arabic_shadda Ù‘ ARABIC SHADDA */
  { 0x05f2, 0x0652 }, /*                Arabic_sukun Ù’ ARABIC SUKUN */

  { 0x0da1, 0x0e01 }, /*                  Thai_kokai à¸� THAI CHARACTER KO KAI */
  { 0x0da2, 0x0e02 }, /*                Thai_khokhai à¸‚ THAI CHARACTER KHO KHAI */
  { 0x0da3, 0x0e03 }, /*               Thai_khokhuat à¸ƒ THAI CHARACTER KHO KHUAT */
  { 0x0da4, 0x0e04 }, /*               Thai_khokhwai à¸„ THAI CHARACTER KHO KHWAI */
  { 0x0da5, 0x0e05 }, /*                Thai_khokhon à¸… THAI CHARACTER KHO KHON */
  { 0x0da6, 0x0e06 }, /*             Thai_khorakhang à¸† THAI CHARACTER KHO RAKHANG */
  { 0x0da7, 0x0e07 }, /*                 Thai_ngongu à¸‡ THAI CHARACTER NGO NGU */
  { 0x0da8, 0x0e08 }, /*                Thai_chochan à¸ˆ THAI CHARACTER CHO CHAN */
  { 0x0da9, 0x0e09 }, /*               Thai_choching à¸‰ THAI CHARACTER CHO CHING */
  { 0x0daa, 0x0e0a }, /*               Thai_chochang à¸Š THAI CHARACTER CHO CHANG */
  { 0x0dab, 0x0e0b }, /*                   Thai_soso à¸‹ THAI CHARACTER SO SO */
  { 0x0dac, 0x0e0c }, /*                Thai_chochoe à¸Œ THAI CHARACTER CHO CHOE */
  { 0x0dad, 0x0e0d }, /*                 Thai_yoying à¸� THAI CHARACTER YO YING */
  { 0x0dae, 0x0e0e }, /*                Thai_dochada à¸Ž THAI CHARACTER DO CHADA */
  { 0x0daf, 0x0e0f }, /*                Thai_topatak à¸� THAI CHARACTER TO PATAK */
  { 0x0db0, 0x0e10 }, /*                Thai_thothan à¸� THAI CHARACTER THO THAN */
  { 0x0db1, 0x0e11 }, /*          Thai_thonangmontho à¸‘ THAI CHARACTER THO NANGMONTHO */
  { 0x0db2, 0x0e12 }, /*             Thai_thophuthao à¸’ THAI CHARACTER THO PHUTHAO */
  { 0x0db3, 0x0e13 }, /*                  Thai_nonen à¸“ THAI CHARACTER NO NEN */
  { 0x0db4, 0x0e14 }, /*                  Thai_dodek à¸” THAI CHARACTER DO DEK */
  { 0x0db5, 0x0e15 }, /*                  Thai_totao à¸• THAI CHARACTER TO TAO */
  { 0x0db6, 0x0e16 }, /*               Thai_thothung à¸– THAI CHARACTER THO THUNG */
  { 0x0db7, 0x0e17 }, /*              Thai_thothahan à¸— THAI CHARACTER THO THAHAN */
  { 0x0db8, 0x0e18 }, /*               Thai_thothong à¸˜ THAI CHARACTER THO THONG */
  { 0x0db9, 0x0e19 }, /*                   Thai_nonu à¸™ THAI CHARACTER NO NU */
  { 0x0dba, 0x0e1a }, /*               Thai_bobaimai à¸š THAI CHARACTER BO BAIMAI */
  { 0x0dbb, 0x0e1b }, /*                  Thai_popla à¸› THAI CHARACTER PO PLA */
  { 0x0dbc, 0x0e1c }, /*               Thai_phophung à¸œ THAI CHARACTER PHO PHUNG */
  { 0x0dbd, 0x0e1d }, /*                   Thai_fofa à¸� THAI CHARACTER FO FA */
  { 0x0dbe, 0x0e1e }, /*                Thai_phophan à¸ž THAI CHARACTER PHO PHAN */
  { 0x0dbf, 0x0e1f }, /*                  Thai_fofan à¸Ÿ THAI CHARACTER FO FAN */
  { 0x0dc0, 0x0e20 }, /*             Thai_phosamphao à¸  THAI CHARACTER PHO SAMPHAO */
  { 0x0dc1, 0x0e21 }, /*                   Thai_moma à¸¡ THAI CHARACTER MO MA */
  { 0x0dc2, 0x0e22 }, /*                  Thai_yoyak à¸¢ THAI CHARACTER YO YAK */
  { 0x0dc3, 0x0e23 }, /*                  Thai_rorua à¸£ THAI CHARACTER RO RUA */
  { 0x0dc4, 0x0e24 }, /*                     Thai_ru à¸¤ THAI CHARACTER RU */
  { 0x0dc5, 0x0e25 }, /*                 Thai_loling à¸¥ THAI CHARACTER LO LING */
  { 0x0dc6, 0x0e26 }, /*                     Thai_lu à¸¦ THAI CHARACTER LU */
  { 0x0dc7, 0x0e27 }, /*                 Thai_wowaen à¸§ THAI CHARACTER WO WAEN */
  { 0x0dc8, 0x0e28 }, /*                 Thai_sosala à¸¨ THAI CHARACTER SO SALA */
  { 0x0dc9, 0x0e29 }, /*                 Thai_sorusi à¸© THAI CHARACTER SO RUSI */
  { 0x0dca, 0x0e2a }, /*                  Thai_sosua à¸ª THAI CHARACTER SO SUA */
  { 0x0dcb, 0x0e2b }, /*                  Thai_hohip à¸« THAI CHARACTER HO HIP */
  { 0x0dcc, 0x0e2c }, /*                Thai_lochula à¸¬ THAI CHARACTER LO CHULA */
  { 0x0dcd, 0x0e2d }, /*                   Thai_oang à¸­ THAI CHARACTER O ANG */
  { 0x0dce, 0x0e2e }, /*               Thai_honokhuk à¸® THAI CHARACTER HO NOKHUK */
  { 0x0dcf, 0x0e2f }, /*              Thai_paiyannoi à¸¯ THAI CHARACTER PAIYANNOI */
  { 0x0dd0, 0x0e30 }, /*                  Thai_saraa à¸° THAI CHARACTER SARA A */
  { 0x0dd1, 0x0e31 }, /*             Thai_maihanakat à¸± THAI CHARACTER MAI HAN-AKAT */
  { 0x0dd2, 0x0e32 }, /*                 Thai_saraaa à¸² THAI CHARACTER SARA AA */
  { 0x0dd3, 0x0e33 }, /*                 Thai_saraam à¸³ THAI CHARACTER SARA AM */
  { 0x0dd4, 0x0e34 }, /*                  Thai_sarai à¸´ THAI CHARACTER SARA I */
  { 0x0dd5, 0x0e35 }, /*                 Thai_saraii à¸µ THAI CHARACTER SARA II */
  { 0x0dd6, 0x0e36 }, /*                 Thai_saraue à¸¶ THAI CHARACTER SARA UE */
  { 0x0dd7, 0x0e37 }, /*                Thai_sarauee à¸· THAI CHARACTER SARA UEE */
  { 0x0dd8, 0x0e38 }, /*                  Thai_sarau à¸¸ THAI CHARACTER SARA U */
  { 0x0dd9, 0x0e39 }, /*                 Thai_sarauu à¸¹ THAI CHARACTER SARA UU */
  { 0x0dda, 0x0e3a }, /*                Thai_phinthu à¸º THAI CHARACTER PHINTHU */
  { 0x0ddf, 0x0e3f }, /*                   Thai_baht à¸¿ THAI CURRENCY SYMBOL BAHT */
  { 0x0de0, 0x0e40 }, /*                  Thai_sarae à¹€ THAI CHARACTER SARA E */
  { 0x0de1, 0x0e41 }, /*                 Thai_saraae à¹� THAI CHARACTER SARA AE */
  { 0x0de2, 0x0e42 }, /*                  Thai_sarao à¹‚ THAI CHARACTER SARA O */
  { 0x0de3, 0x0e43 }, /*          Thai_saraaimaimuan à¹ƒ THAI CHARACTER SARA AI MAIMUAN */
  { 0x0de4, 0x0e44 }, /*         Thai_saraaimaimalai à¹„ THAI CHARACTER SARA AI MAIMALAI */
  { 0x0de5, 0x0e45 }, /*            Thai_lakkhangyao à¹… THAI CHARACTER LAKKHANGYAO */
  { 0x0de6, 0x0e46 }, /*               Thai_maiyamok à¹† THAI CHARACTER MAIYAMOK */
  { 0x0de7, 0x0e47 }, /*              Thai_maitaikhu à¹‡ THAI CHARACTER MAITAIKHU */
  { 0x0de8, 0x0e48 }, /*                  Thai_maiek à¹ˆ THAI CHARACTER MAI EK */
  { 0x0de9, 0x0e49 }, /*                 Thai_maitho à¹‰ THAI CHARACTER MAI THO */
  { 0x0dea, 0x0e4a }, /*                 Thai_maitri à¹Š THAI CHARACTER MAI TRI */
  { 0x0deb, 0x0e4b }, /*            Thai_maichattawa à¹‹ THAI CHARACTER MAI CHATTAWA */
  { 0x0dec, 0x0e4c }, /*            Thai_thanthakhat à¹Œ THAI CHARACTER THANTHAKHAT */
  { 0x0ded, 0x0e4d }, /*               Thai_nikhahit à¹� THAI CHARACTER NIKHAHIT */
  { 0x0df0, 0x0e50 }, /*                 Thai_leksun à¹� THAI DIGIT ZERO */
  { 0x0df1, 0x0e51 }, /*                Thai_leknung à¹‘ THAI DIGIT ONE */
  { 0x0df2, 0x0e52 }, /*                Thai_leksong à¹’ THAI DIGIT TWO */
  { 0x0df3, 0x0e53 }, /*                 Thai_leksam à¹“ THAI DIGIT THREE */
  { 0x0df4, 0x0e54 }, /*                  Thai_leksi à¹” THAI DIGIT FOUR */
  { 0x0df5, 0x0e55 }, /*                  Thai_lekha à¹• THAI DIGIT FIVE */
  { 0x0df6, 0x0e56 }, /*                 Thai_lekhok à¹– THAI DIGIT SIX */
  { 0x0df7, 0x0e57 }, /*                Thai_lekchet à¹— THAI DIGIT SEVEN */
  { 0x0df8, 0x0e58 }, /*                Thai_lekpaet à¹˜ THAI DIGIT EIGHT */
  { 0x0df9, 0x0e59 }, /*                 Thai_lekkao à¹™ THAI DIGIT NINE */

  { 0x0ed4, 0x11a8 }, /*             Hangul_J_Kiyeog á†¨ HANGUL JONGSEONG KIYEOK */
  { 0x0ed5, 0x11a9 }, /*        Hangul_J_SsangKiyeog á†© HANGUL JONGSEONG SSANGKIYEOK */
  { 0x0ed6, 0x11aa }, /*         Hangul_J_KiyeogSios á†ª HANGUL JONGSEONG KIYEOK-SIOS */
  { 0x0ed7, 0x11ab }, /*              Hangul_J_Nieun á†« HANGUL JONGSEONG NIEUN */
  { 0x0ed8, 0x11ac }, /*         Hangul_J_NieunJieuj á†¬ HANGUL JONGSEONG NIEUN-CIEUC */
  { 0x0ed9, 0x11ad }, /*         Hangul_J_NieunHieuh á†­ HANGUL JONGSEONG NIEUN-HIEUH */
  { 0x0eda, 0x11ae }, /*             Hangul_J_Dikeud á†® HANGUL JONGSEONG TIKEUT */
  { 0x0edb, 0x11af }, /*              Hangul_J_Rieul á†¯ HANGUL JONGSEONG RIEUL */
  { 0x0edc, 0x11b0 }, /*        Hangul_J_RieulKiyeog á†° HANGUL JONGSEONG RIEUL-KIYEOK */
  { 0x0edd, 0x11b1 }, /*         Hangul_J_RieulMieum á†± HANGUL JONGSEONG RIEUL-MIEUM */
  { 0x0ede, 0x11b2 }, /*         Hangul_J_RieulPieub á†² HANGUL JONGSEONG RIEUL-PIEUP */
  { 0x0edf, 0x11b3 }, /*          Hangul_J_RieulSios á†³ HANGUL JONGSEONG RIEUL-SIOS */
  { 0x0ee0, 0x11b4 }, /*         Hangul_J_RieulTieut á†´ HANGUL JONGSEONG RIEUL-THIEUTH */
  { 0x0ee1, 0x11b5 }, /*        Hangul_J_RieulPhieuf á†µ HANGUL JONGSEONG RIEUL-PHIEUPH */
  { 0x0ee2, 0x11b6 }, /*         Hangul_J_RieulHieuh á†¶ HANGUL JONGSEONG RIEUL-HIEUH */
  { 0x0ee3, 0x11b7 }, /*              Hangul_J_Mieum á†· HANGUL JONGSEONG MIEUM */
  { 0x0ee4, 0x11b8 }, /*              Hangul_J_Pieub á†¸ HANGUL JONGSEONG PIEUP */
  { 0x0ee5, 0x11b9 }, /*          Hangul_J_PieubSios á†¹ HANGUL JONGSEONG PIEUP-SIOS */
  { 0x0ee6, 0x11ba }, /*               Hangul_J_Sios á†º HANGUL JONGSEONG SIOS */
  { 0x0ee7, 0x11bb }, /*          Hangul_J_SsangSios á†» HANGUL JONGSEONG SSANGSIOS */
  { 0x0ee8, 0x11bc }, /*              Hangul_J_Ieung á†¼ HANGUL JONGSEONG IEUNG */
  { 0x0ee9, 0x11bd }, /*              Hangul_J_Jieuj á†½ HANGUL JONGSEONG CIEUC */
  { 0x0eea, 0x11be }, /*              Hangul_J_Cieuc á†¾ HANGUL JONGSEONG CHIEUCH */
  { 0x0eeb, 0x11bf }, /*             Hangul_J_Khieuq á†¿ HANGUL JONGSEONG KHIEUKH */
  { 0x0eec, 0x11c0 }, /*              Hangul_J_Tieut á‡€ HANGUL JONGSEONG THIEUTH */
  { 0x0eed, 0x11c1 }, /*             Hangul_J_Phieuf á‡� HANGUL JONGSEONG PHIEUPH */
  { 0x0eee, 0x11c2 }, /*              Hangul_J_Hieuh á‡‚ HANGUL JONGSEONG HIEUH */
  { 0x0ef8, 0x11eb }, /*            Hangul_J_PanSios á‡« HANGUL JONGSEONG PANSIOS */
  { 0x0ef9, 0x11f0 }, /*  Hangul_J_KkogjiDalrinIeung á‡° HANGUL JONGSEONG YESIEUNG */
  { 0x0efa, 0x11f9 }, /*        Hangul_J_YeorinHieuh á‡¹ HANGUL JONGSEONG YEORINHIEUH */


  { 0x0aa2, 0x2002 }, /*                     enspace â€‚ EN SPACE */
  { 0x0aa1, 0x2003 }, /*                     emspace â€ƒ EM SPACE */
  { 0x0aa3, 0x2004 }, /*                    em3space â€„ THREE-PER-EM SPACE */
  { 0x0aa4, 0x2005 }, /*                    em4space â€… FOUR-PER-EM SPACE */
  { 0x0aa5, 0x2007 }, /*                  digitspace â€‡ FIGURE SPACE */
  { 0x0aa6, 0x2008 }, /*                  punctspace â€ˆ PUNCTUATION SPACE */
  { 0x0aa7, 0x2009 }, /*                   thinspace â€‰ THIN SPACE */
  { 0x0aa8, 0x200a }, /*                   hairspace â€Š HAIR SPACE */
  { 0x0abb, 0x2012 }, /*                     figdash â€’ FIGURE DASH */
  { 0x0aaa, 0x2013 }, /*                      endash â€“ EN DASH */
  { 0x0aa9, 0x2014 }, /*                      emdash â€” EM DASH */
  { 0x07af, 0x2015 }, /*              Greek_horizbar â€• HORIZONTAL BAR */
  { 0x0cdf, 0x2017 }, /*        hebrew_doublelowline â€— DOUBLE LOW LINE */
  { 0x0ad0, 0x2018 }, /*         leftsinglequotemark â€˜ LEFT SINGLE QUOTATION MARK */
  { 0x0ad1, 0x2019 }, /*        rightsinglequotemark â€™ RIGHT SINGLE QUOTATION MARK */
  { 0x0afd, 0x201a }, /*          singlelowquotemark â€š SINGLE LOW-9 QUOTATION MARK */
  { 0x0ad2, 0x201c }, /*         leftdoublequotemark â€œ LEFT DOUBLE QUOTATION MARK */
  { 0x0ad3, 0x201d }, /*        rightdoublequotemark â€� RIGHT DOUBLE QUOTATION MARK */
  { 0x0afe, 0x201e }, /*          doublelowquotemark â€ž DOUBLE LOW-9 QUOTATION MARK */
  { 0x0af1, 0x2020 }, /*                      dagger â€  DAGGER */
  { 0x0af2, 0x2021 }, /*                doubledagger â€¡ DOUBLE DAGGER */
  { 0x0ae6, 0x2022 }, /*          enfilledcircbullet â€¢ BULLET */
  { 0x0aaf, 0x2025 }, /*             doubbaselinedot â€¥ TWO DOT LEADER */
  { 0x0aae, 0x2026 }, /*                    ellipsis â€¦ HORIZONTAL ELLIPSIS */
  { 0x0ad6, 0x2032 }, /*                     minutes â€² PRIME */
  { 0x0ad7, 0x2033 }, /*                     seconds â€³ DOUBLE PRIME */
  { 0x0afc, 0x2038 }, /*                       caret â€¸ CARET */
  { 0x047e, 0x203e }, /*                    overline â€¾ OVERLINE */
  { 0x0eff, 0x20a9 }, /*                  Korean_Won â‚© WON SIGN */
  //{ 0x13a4, 0x20ac }, /*                        Euro â‚¬ EURO SIGN */

  { 0x0ab8, 0x2105 }, /*                      careof â„… CARE OF */
  { 0x06b0, 0x2116 }, /*                  numerosign â„– NUMERO SIGN */
  { 0x0afb, 0x2117 }, /*         phonographcopyright â„— SOUND RECORDING COPYRIGHT */
  { 0x0ad4, 0x211e }, /*                prescription â„ž PRESCRIPTION TAKE */
  { 0x0ac9, 0x2122 }, /*                   trademark â„¢ TRADE MARK SIGN */
  { 0x0ab0, 0x2153 }, /*                    onethird â…“ VULGAR FRACTION ONE THIRD */
  { 0x0ab1, 0x2154 }, /*                   twothirds â…” VULGAR FRACTION TWO THIRDS */
  { 0x0ab2, 0x2155 }, /*                    onefifth â…• VULGAR FRACTION ONE FIFTH */
  { 0x0ab3, 0x2156 }, /*                   twofifths â…– VULGAR FRACTION TWO FIFTHS */
  { 0x0ab4, 0x2157 }, /*                 threefifths â…— VULGAR FRACTION THREE FIFTHS */
  { 0x0ab5, 0x2158 }, /*                  fourfifths â…˜ VULGAR FRACTION FOUR FIFTHS */
  { 0x0ab6, 0x2159 }, /*                    onesixth â…™ VULGAR FRACTION ONE SIXTH */
  { 0x0ab7, 0x215a }, /*                  fivesixths â…š VULGAR FRACTION FIVE SIXTHS */
  { 0x0ac3, 0x215b }, /*                   oneeighth â…› VULGAR FRACTION ONE EIGHTH */
  { 0x0ac4, 0x215c }, /*                threeeighths â…œ VULGAR FRACTION THREE EIGHTHS */
  { 0x0ac5, 0x215d }, /*                 fiveeighths â…� VULGAR FRACTION FIVE EIGHTHS */
  { 0x0ac6, 0x215e }, /*                seveneighths â…ž VULGAR FRACTION SEVEN EIGHTHS */
  { 0x08fb, 0x2190 }, /*                   leftarrow â†� LEFTWARDS ARROW */
  { 0x08fc, 0x2191 }, /*                     uparrow â†‘ UPWARDS ARROW */
  { 0x08fd, 0x2192 }, /*                  rightarrow â†’ RIGHTWARDS ARROW */
  { 0x08fe, 0x2193 }, /*                   downarrow â†“ DOWNWARDS ARROW */
  { 0x08ce, 0x21d2 }, /*                     implies â‡’ RIGHTWARDS DOUBLE ARROW */
  { 0x08cd, 0x21d4 }, /*                    ifonlyif â‡” LEFT RIGHT DOUBLE ARROW */
  { 0x08ef, 0x2202 }, /*           partialderivative âˆ‚ PARTIAL DIFFERENTIAL */
  { 0x08c5, 0x2207 }, /*                       nabla âˆ‡ NABLA */
  { 0x0bca, 0x2218 }, /*                         jot âˆ˜ RING OPERATOR */
  { 0x08d6, 0x221a }, /*                     radical âˆš SQUARE ROOT */
  { 0x08c1, 0x221d }, /*                   variation âˆ� PROPORTIONAL TO */
  { 0x08c2, 0x221e }, /*                    infinity âˆž INFINITY */
  { 0x08de, 0x2227 }, /*                  logicaland âˆ§ LOGICAL AND */
  { 0x08df, 0x2228 }, /*                   logicalor âˆ¨ LOGICAL OR */
  { 0x08dc, 0x2229 }, /*                intersection âˆ© INTERSECTION */
  { 0x08dd, 0x222a }, /*                       union âˆª UNION */
  { 0x08bf, 0x222b }, /*                    integral âˆ« INTEGRAL */
  { 0x08c0, 0x2234 }, /*                   therefore âˆ´ THEREFORE */
  { 0x08c8, 0x223c }, /*                 approximate âˆ¼ TILDE OPERATOR */
  { 0x08c9, 0x2243 }, /*                similarequal â‰ƒ ASYMPTOTICALLY EQUAL TO */
  { 0x08bd, 0x2260 }, /*                    notequal â‰  NOT EQUAL TO */
  { 0x08cf, 0x2261 }, /*                   identical â‰¡ IDENTICAL TO */
  { 0x08bc, 0x2264 }, /*               lessthanequal â‰¤ LESS-THAN OR EQUAL TO */
  { 0x08be, 0x2265 }, /*            greaterthanequal â‰¥ GREATER-THAN OR EQUAL TO */
  { 0x08da, 0x2282 }, /*                  includedin âŠ‚ SUBSET OF */
  { 0x08db, 0x2283 }, /*                    includes âŠƒ SUPERSET OF */
  { 0x0bdc, 0x22a2 }, /*                    lefttack âŠ¢ RIGHT TACK */
  { 0x0bfc, 0x22a3 }, /*                   righttack âŠ£ LEFT TACK */
  { 0x0bce, 0x22a4 }, /*                      uptack âŠ¤ DOWN TACK */
  { 0x0bc2, 0x22a5 }, /*                    downtack âŠ¥ UP TACK */
  { 0x0bd3, 0x2308 }, /*                     upstile âŒˆ LEFT CEILING */
  { 0x0bc4, 0x230a }, /*                   downstile âŒŠ LEFT FLOOR */
  { 0x0afa, 0x2315 }, /*           telephonerecorder âŒ• TELEPHONE RECORDER */
  { 0x08a4, 0x2320 }, /*                 topintegral âŒ  TOP HALF INTEGRAL */
  { 0x08a5, 0x2321 }, /*                 botintegral âŒ¡ BOTTOM HALF INTEGRAL */
  { 0x0abc, 0x2329 }, /*            leftanglebracket âŒ© LEFT-POINTING ANGLE BRACKET */
  { 0x0abe, 0x232a }, /*           rightanglebracket âŒª RIGHT-POINTING ANGLE BRACKET */
  { 0x0bcc, 0x2395 }, /*                        quad âŽ• APL FUNCTIONAL SYMBOL QUAD */
  { 0x08ab, 0x239b }, /*               topleftparens âŽ› ??? */
  { 0x08ac, 0x239d }, /*               botleftparens âŽ� ??? */
  { 0x08ad, 0x239e }, /*              toprightparens âŽž ??? */
  { 0x08ae, 0x23a0 }, /*              botrightparens âŽ  ??? */
  { 0x08a7, 0x23a1 }, /*            topleftsqbracket âŽ¡ ??? */
  { 0x08a8, 0x23a3 }, /*            botleftsqbracket âŽ£ ??? */
  { 0x08a9, 0x23a4 }, /*           toprightsqbracket âŽ¤ ??? */
  { 0x08aa, 0x23a6 }, /*           botrightsqbracket âŽ¦ ??? */
  { 0x08af, 0x23a8 }, /*        leftmiddlecurlybrace âŽ¨ ??? */
  { 0x08b0, 0x23ac }, /*       rightmiddlecurlybrace âŽ¬ ??? */
  { 0x08a1, 0x23b7 }, /*                 leftradical âŽ· ??? */
  { 0x09ef, 0x23ba }, /*              horizlinescan1 âŽº HORIZONTAL SCAN LINE-1 (Unicode 3.2 draft) */
  { 0x09f0, 0x23bb }, /*              horizlinescan3 âŽ» HORIZONTAL SCAN LINE-3 (Unicode 3.2 draft) */
  { 0x09f2, 0x23bc }, /*              horizlinescan7 âŽ¼ HORIZONTAL SCAN LINE-7 (Unicode 3.2 draft) */
  { 0x09f3, 0x23bd }, /*              horizlinescan9 âŽ½ HORIZONTAL SCAN LINE-9 (Unicode 3.2 draft) */
  { 0x09e2, 0x2409 }, /*                          ht â�‰ SYMBOL FOR HORIZONTAL TABULATION */
  { 0x09e3, 0x240c }, /*                          ff â�Œ SYMBOL FOR FORM FEED */
  { 0x09e4, 0x240d }, /*                          cr â�� SYMBOL FOR CARRIAGE RETURN */
  { 0x09e5, 0x240a }, /*                          lf â�Š SYMBOL FOR LINE FEED */
  { 0x09e8, 0x2424 }, /*                          nl â�¤ SYMBOL FOR NEWLINE */
  { 0x09e9, 0x240b }, /*                          vt â�‹ SYMBOL FOR VERTICAL TABULATION */

  { 0x08a3, 0x2500 }, /*              horizconnector â”€ BOX DRAWINGS LIGHT HORIZONTAL */
  { 0x08a6, 0x2502 }, /*               vertconnector â”‚ BOX DRAWINGS LIGHT VERTICAL */
  { 0x08a2, 0x250c }, /*              topleftradical â”Œ BOX DRAWINGS LIGHT DOWN AND RIGHT */
  { 0x09ec, 0x250c }, /*                upleftcorner â”Œ BOX DRAWINGS LIGHT DOWN AND RIGHT */
  { 0x09eb, 0x2510 }, /*               uprightcorner â”� BOX DRAWINGS LIGHT DOWN AND LEFT */
  { 0x09ed, 0x2514 }, /*               lowleftcorner â”” BOX DRAWINGS LIGHT UP AND RIGHT */
  { 0x09ea, 0x2518 }, /*              lowrightcorner â”˜ BOX DRAWINGS LIGHT UP AND LEFT */
  { 0x09f4, 0x251c }, /*                       leftt â”œ BOX DRAWINGS LIGHT VERTICAL AND RIGHT */
  { 0x09f5, 0x2524 }, /*                      rightt â”¤ BOX DRAWINGS LIGHT VERTICAL AND LEFT */
  { 0x09f7, 0x252c }, /*                        topt â”¬ BOX DRAWINGS LIGHT DOWN AND HORIZONTAL */
  { 0x09ee, 0x253c }, /*               crossinglines â”¼ BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL */
  { 0x09f6, 0x2534 }, /*                        bott â”´ BOX DRAWINGS LIGHT UP AND HORIZONTAL */
  { 0x09e1, 0x2592 }, /*                checkerboard â–’ MEDIUM SHADE */
  { 0x0ae7, 0x25aa }, /*            enfilledsqbullet â–ª BLACK SMALL SQUARE */
  { 0x0ae1, 0x25ab }, /*          enopensquarebullet â–« WHITE SMALL SQUARE */
  { 0x0adb, 0x25ac }, /*            filledrectbullet â–¬ BLACK RECTANGLE */
  { 0x0ae2, 0x25ad }, /*              openrectbullet â–­ WHITE RECTANGLE */
  { 0x0adf, 0x25ae }, /*                emfilledrect â–® BLACK VERTICAL RECTANGLE */
  { 0x0acf, 0x25af }, /*             emopenrectangle â–¯ WHITE VERTICAL RECTANGLE */
  { 0x0ae8, 0x25b2 }, /*           filledtribulletup â–² BLACK UP-POINTING TRIANGLE */
  { 0x0ae3, 0x25b3 }, /*             opentribulletup â–³ WHITE UP-POINTING TRIANGLE */
  { 0x0add, 0x25b6 }, /*        filledrighttribullet â–¶ BLACK RIGHT-POINTING TRIANGLE */
  { 0x0acd, 0x25b7 }, /*           rightopentriangle â–· WHITE RIGHT-POINTING TRIANGLE */
  { 0x0ae9, 0x25bc }, /*         filledtribulletdown â–¼ BLACK DOWN-POINTING TRIANGLE */
  { 0x0ae4, 0x25bd }, /*           opentribulletdown â–½ WHITE DOWN-POINTING TRIANGLE */
  { 0x0adc, 0x25c0 }, /*         filledlefttribullet â—€ BLACK LEFT-POINTING TRIANGLE */
  { 0x0acc, 0x25c1 }, /*            leftopentriangle â—� WHITE LEFT-POINTING TRIANGLE */
  { 0x09e0, 0x25c6 }, /*                soliddiamond â—† BLACK DIAMOND */
  { 0x0ace, 0x25cb }, /*                emopencircle â—‹ WHITE CIRCLE */
  { 0x0ade, 0x25cf }, /*              emfilledcircle â—� BLACK CIRCLE */
  { 0x0ae0, 0x25e6 }, /*            enopencircbullet â—¦ WHITE BULLET */
  { 0x0aee, 0x2665 }, /*                       heart â™¥ BLACK HEART SUIT */
  { 0x0aed, 0x2666 }, /*                     diamond â™¦ BLACK DIAMOND SUIT */
  { 0x0af5, 0x266f }, /*                musicalsharp â™¯ MUSIC SHARP SIGN */
  { 0x0af6, 0x266d }, /*                 musicalflat â™­ MUSIC FLAT SIGN */
  { 0x0af3, 0x2713 }, /*                   checkmark âœ“ CHECK MARK */
  { 0x0af4, 0x2717 }, /*                 ballotcross âœ— BALLOT X */
  { 0x0ad9, 0x271d }, /*                  latincross âœ� LATIN CROSS */
  { 0x0af0, 0x2720 }, /*                maltesecross âœ  MALTESE CROSS */

  { 0x04a4, 0x3001 }, /*                  kana_comma ã€� IDEOGRAPHIC COMMA */
  { 0x04a1, 0x3002 }, /*               kana_fullstop ã€‚ IDEOGRAPHIC FULL STOP */
  { 0x04a2, 0x300c }, /*         kana_openingbracket ã€Œ LEFT CORNER BRACKET */
  { 0x04a3, 0x300d }, /*         kana_closingbracket ã€� RIGHT CORNER BRACKET */
  { 0x04de, 0x309b }, /*                 voicedsound ã‚› KATAKANA-HIRAGANA VOICED SOUND MARK */
  { 0x04df, 0x309c }, /*             semivoicedsound ã‚œ KATAKANA-HIRAGANA SEMI-VOICED SOUND MARK */
  { 0x04a7, 0x30a1 }, /*                      kana_a ã‚¡ KATAKANA LETTER SMALL A */
  { 0x04b1, 0x30a2 }, /*                      kana_A ã‚¢ KATAKANA LETTER A */
  { 0x04a8, 0x30a3 }, /*                      kana_i ã‚£ KATAKANA LETTER SMALL I */
  { 0x04b2, 0x30a4 }, /*                      kana_I ã‚¤ KATAKANA LETTER I */
  { 0x04a9, 0x30a5 }, /*                      kana_u ã‚¥ KATAKANA LETTER SMALL U */
  { 0x04b3, 0x30a6 }, /*                      kana_U ã‚¦ KATAKANA LETTER U */
  { 0x04aa, 0x30a7 }, /*                      kana_e ã‚§ KATAKANA LETTER SMALL E */
  { 0x04b4, 0x30a8 }, /*                      kana_E ã‚¨ KATAKANA LETTER E */
  { 0x04ab, 0x30a9 }, /*                      kana_o ã‚© KATAKANA LETTER SMALL O */
  { 0x04b5, 0x30aa }, /*                      kana_O ã‚ª KATAKANA LETTER O */
  { 0x04b6, 0x30ab }, /*                     kana_KA ã‚« KATAKANA LETTER KA */
  { 0x04b7, 0x30ad }, /*                     kana_KI ã‚­ KATAKANA LETTER KI */
  { 0x04b8, 0x30af }, /*                     kana_KU ã‚¯ KATAKANA LETTER KU */
  { 0x04b9, 0x30b1 }, /*                     kana_KE ã‚± KATAKANA LETTER KE */
  { 0x04ba, 0x30b3 }, /*                     kana_KO ã‚³ KATAKANA LETTER KO */
  { 0x04bb, 0x30b5 }, /*                     kana_SA ã‚µ KATAKANA LETTER SA */
  { 0x04bc, 0x30b7 }, /*                    kana_SHI ã‚· KATAKANA LETTER SI */
  { 0x04bd, 0x30b9 }, /*                     kana_SU ã‚¹ KATAKANA LETTER SU */
  { 0x04be, 0x30bb }, /*                     kana_SE ã‚» KATAKANA LETTER SE */
  { 0x04bf, 0x30bd }, /*                     kana_SO ã‚½ KATAKANA LETTER SO */
  { 0x04c0, 0x30bf }, /*                     kana_TA ã‚¿ KATAKANA LETTER TA */
  { 0x04c1, 0x30c1 }, /*                    kana_CHI ãƒ� KATAKANA LETTER TI */
  { 0x04af, 0x30c3 }, /*                    kana_tsu ãƒƒ KATAKANA LETTER SMALL TU */
  { 0x04c2, 0x30c4 }, /*                    kana_TSU ãƒ„ KATAKANA LETTER TU */
  { 0x04c3, 0x30c6 }, /*                     kana_TE ãƒ† KATAKANA LETTER TE */
  { 0x04c4, 0x30c8 }, /*                     kana_TO ãƒˆ KATAKANA LETTER TO */
  { 0x04c5, 0x30ca }, /*                     kana_NA ãƒŠ KATAKANA LETTER NA */
  { 0x04c6, 0x30cb }, /*                     kana_NI ãƒ‹ KATAKANA LETTER NI */
  { 0x04c7, 0x30cc }, /*                     kana_NU ãƒŒ KATAKANA LETTER NU */
  { 0x04c8, 0x30cd }, /*                     kana_NE ãƒ� KATAKANA LETTER NE */
  { 0x04c9, 0x30ce }, /*                     kana_NO ãƒŽ KATAKANA LETTER NO */
  { 0x04ca, 0x30cf }, /*                     kana_HA ãƒ� KATAKANA LETTER HA */
  { 0x04cb, 0x30d2 }, /*                     kana_HI ãƒ’ KATAKANA LETTER HI */
  { 0x04cc, 0x30d5 }, /*                     kana_FU ãƒ• KATAKANA LETTER HU */
  { 0x04cd, 0x30d8 }, /*                     kana_HE ãƒ˜ KATAKANA LETTER HE */
  { 0x04ce, 0x30db }, /*                     kana_HO ãƒ› KATAKANA LETTER HO */
  { 0x04cf, 0x30de }, /*                     kana_MA ãƒž KATAKANA LETTER MA */
  { 0x04d0, 0x30df }, /*                     kana_MI ãƒŸ KATAKANA LETTER MI */
  { 0x04d1, 0x30e0 }, /*                     kana_MU ãƒ  KATAKANA LETTER MU */
  { 0x04d2, 0x30e1 }, /*                     kana_ME ãƒ¡ KATAKANA LETTER ME */
  { 0x04d3, 0x30e2 }, /*                     kana_MO ãƒ¢ KATAKANA LETTER MO */
  { 0x04ac, 0x30e3 }, /*                     kana_ya ãƒ£ KATAKANA LETTER SMALL YA */
  { 0x04d4, 0x30e4 }, /*                     kana_YA ãƒ¤ KATAKANA LETTER YA */
  { 0x04ad, 0x30e5 }, /*                     kana_yu ãƒ¥ KATAKANA LETTER SMALL YU */
  { 0x04d5, 0x30e6 }, /*                     kana_YU ãƒ¦ KATAKANA LETTER YU */
  { 0x04ae, 0x30e7 }, /*                     kana_yo ãƒ§ KATAKANA LETTER SMALL YO */
  { 0x04d6, 0x30e8 }, /*                     kana_YO ãƒ¨ KATAKANA LETTER YO */
  { 0x04d7, 0x30e9 }, /*                     kana_RA ãƒ© KATAKANA LETTER RA */
  { 0x04d8, 0x30ea }, /*                     kana_RI ãƒª KATAKANA LETTER RI */
  { 0x04d9, 0x30eb }, /*                     kana_RU ãƒ« KATAKANA LETTER RU */
  { 0x04da, 0x30ec }, /*                     kana_RE ãƒ¬ KATAKANA LETTER RE */
  { 0x04db, 0x30ed }, /*                     kana_RO ãƒ­ KATAKANA LETTER RO */
  { 0x04dc, 0x30ef }, /*                     kana_WA ãƒ¯ KATAKANA LETTER WA */
  { 0x04a6, 0x30f2 }, /*                     kana_WO ãƒ² KATAKANA LETTER WO */
  { 0x04dd, 0x30f3 }, /*                      kana_N ãƒ³ KATAKANA LETTER N */
  { 0x04a5, 0x30fb }, /*            kana_conjunctive ãƒ» KATAKANA MIDDLE DOT */
  { 0x04b0, 0x30fc }, /*              prolongedsound ãƒ¼ KATAKANA-HIRAGANA PROLONGED SOUND MARK */

  { 0x0ea1, 0x3131 }, /*               Hangul_Kiyeog ã„± HANGUL LETTER KIYEOK */
  { 0x0ea2, 0x3132 }, /*          Hangul_SsangKiyeog ã„² HANGUL LETTER SSANGKIYEOK */
  { 0x0ea3, 0x3133 }, /*           Hangul_KiyeogSios ã„³ HANGUL LETTER KIYEOK-SIOS */
  { 0x0ea4, 0x3134 }, /*                Hangul_Nieun ã„´ HANGUL LETTER NIEUN */
  { 0x0ea5, 0x3135 }, /*           Hangul_NieunJieuj ã„µ HANGUL LETTER NIEUN-CIEUC */
  { 0x0ea6, 0x3136 }, /*           Hangul_NieunHieuh ã„¶ HANGUL LETTER NIEUN-HIEUH */
  { 0x0ea7, 0x3137 }, /*               Hangul_Dikeud ã„· HANGUL LETTER TIKEUT */
  { 0x0ea8, 0x3138 }, /*          Hangul_SsangDikeud ã„¸ HANGUL LETTER SSANGTIKEUT */
  { 0x0ea9, 0x3139 }, /*                Hangul_Rieul ã„¹ HANGUL LETTER RIEUL */
  { 0x0eaa, 0x313a }, /*          Hangul_RieulKiyeog ã„º HANGUL LETTER RIEUL-KIYEOK */
  { 0x0eab, 0x313b }, /*           Hangul_RieulMieum ã„» HANGUL LETTER RIEUL-MIEUM */
  { 0x0eac, 0x313c }, /*           Hangul_RieulPieub ã„¼ HANGUL LETTER RIEUL-PIEUP */
  { 0x0ead, 0x313d }, /*            Hangul_RieulSios ã„½ HANGUL LETTER RIEUL-SIOS */
  { 0x0eae, 0x313e }, /*           Hangul_RieulTieut ã„¾ HANGUL LETTER RIEUL-THIEUTH */
  { 0x0eaf, 0x313f }, /*          Hangul_RieulPhieuf ã„¿ HANGUL LETTER RIEUL-PHIEUPH */
  { 0x0eb0, 0x3140 }, /*           Hangul_RieulHieuh ã…€ HANGUL LETTER RIEUL-HIEUH */
  { 0x0eb1, 0x3141 }, /*                Hangul_Mieum ã…� HANGUL LETTER MIEUM */
  { 0x0eb2, 0x3142 }, /*                Hangul_Pieub ã…‚ HANGUL LETTER PIEUP */
  { 0x0eb3, 0x3143 }, /*           Hangul_SsangPieub ã…ƒ HANGUL LETTER SSANGPIEUP */
  { 0x0eb4, 0x3144 }, /*            Hangul_PieubSios ã…„ HANGUL LETTER PIEUP-SIOS */
  { 0x0eb5, 0x3145 }, /*                 Hangul_Sios ã…… HANGUL LETTER SIOS */
  { 0x0eb6, 0x3146 }, /*            Hangul_SsangSios ã…† HANGUL LETTER SSANGSIOS */
  { 0x0eb7, 0x3147 }, /*                Hangul_Ieung ã…‡ HANGUL LETTER IEUNG */
  { 0x0eb8, 0x3148 }, /*                Hangul_Jieuj ã…ˆ HANGUL LETTER CIEUC */
  { 0x0eb9, 0x3149 }, /*           Hangul_SsangJieuj ã…‰ HANGUL LETTER SSANGCIEUC */
  { 0x0eba, 0x314a }, /*                Hangul_Cieuc ã…Š HANGUL LETTER CHIEUCH */
  { 0x0ebb, 0x314b }, /*               Hangul_Khieuq ã…‹ HANGUL LETTER KHIEUKH */
  { 0x0ebc, 0x314c }, /*                Hangul_Tieut ã…Œ HANGUL LETTER THIEUTH */
  { 0x0ebd, 0x314d }, /*               Hangul_Phieuf ã…� HANGUL LETTER PHIEUPH */
  { 0x0ebe, 0x314e }, /*                Hangul_Hieuh ã…Ž HANGUL LETTER HIEUH */
  { 0x0ebf, 0x314f }, /*                    Hangul_A ã…� HANGUL LETTER A */
  { 0x0ec0, 0x3150 }, /*                   Hangul_AE ã…� HANGUL LETTER AE */
  { 0x0ec1, 0x3151 }, /*                   Hangul_YA ã…‘ HANGUL LETTER YA */
  { 0x0ec2, 0x3152 }, /*                  Hangul_YAE ã…’ HANGUL LETTER YAE */
  { 0x0ec3, 0x3153 }, /*                   Hangul_EO ã…“ HANGUL LETTER EO */
  { 0x0ec4, 0x3154 }, /*                    Hangul_E ã…” HANGUL LETTER E */
  { 0x0ec5, 0x3155 }, /*                  Hangul_YEO ã…• HANGUL LETTER YEO */
  { 0x0ec6, 0x3156 }, /*                   Hangul_YE ã…– HANGUL LETTER YE */
  { 0x0ec7, 0x3157 }, /*                    Hangul_O ã…— HANGUL LETTER O */
  { 0x0ec8, 0x3158 }, /*                   Hangul_WA ã…˜ HANGUL LETTER WA */
  { 0x0ec9, 0x3159 }, /*                  Hangul_WAE ã…™ HANGUL LETTER WAE */
  { 0x0eca, 0x315a }, /*                   Hangul_OE ã…š HANGUL LETTER OE */
  { 0x0ecb, 0x315b }, /*                   Hangul_YO ã…› HANGUL LETTER YO */
  { 0x0ecc, 0x315c }, /*                    Hangul_U ã…œ HANGUL LETTER U */
  { 0x0ecd, 0x315d }, /*                  Hangul_WEO ã…� HANGUL LETTER WEO */
  { 0x0ece, 0x315e }, /*                   Hangul_WE ã…ž HANGUL LETTER WE */
  { 0x0ecf, 0x315f }, /*                   Hangul_WI ã…Ÿ HANGUL LETTER WI */
  { 0x0ed0, 0x3160 }, /*                   Hangul_YU ã…  HANGUL LETTER YU */
  { 0x0ed1, 0x3161 }, /*                   Hangul_EU ã…¡ HANGUL LETTER EU */
  { 0x0ed2, 0x3162 }, /*                   Hangul_YI ã…¢ HANGUL LETTER YI */
  { 0x0ed3, 0x3163 }, /*                    Hangul_I ã…£ HANGUL LETTER I */
  { 0x0eef, 0x316d }, /*     Hangul_RieulYeorinHieuh ã…­ HANGUL LETTER RIEUL-YEORINHIEUH */
  { 0x0ef0, 0x3171 }, /*    Hangul_SunkyeongeumMieum ã…± HANGUL LETTER KAPYEOUNMIEUM */
  { 0x0ef1, 0x3178 }, /*    Hangul_SunkyeongeumPieub ã…¸ HANGUL LETTER KAPYEOUNPIEUP */
  { 0x0ef2, 0x317f }, /*              Hangul_PanSios ã…¿ HANGUL LETTER PANSIOS */
  { 0x0ef3, 0x3181 }, /*    Hangul_KkogjiDalrinIeung ã†� HANGUL LETTER YESIEUNG */
  { 0x0ef4, 0x3184 }, /*   Hangul_SunkyeongeumPhieuf ã†„ HANGUL LETTER KAPYEOUNPHIEUPH */
  { 0x0ef5, 0x3186 }, /*          Hangul_YeorinHieuh ã†† HANGUL LETTER YEORINHIEUH */
  { 0x0ef6, 0x318d }, /*                Hangul_AraeA ã†� HANGUL LETTER ARAEA */
  { 0x0ef7, 0x318e }, /*               Hangul_AraeAE ã†Ž HANGUL LETTER ARAEAE */
 };

KeySym ucs2keysym (long ucs)
{
    int min = 0;
    int max = sizeof(keysymtab) / sizeof(struct codepair) - 1;
    int mid;

    /* first check for Latin-1 characters (1:1 mapping) */
    if ((ucs >= 0x0020 && ucs <= 0x007e) ||
        (ucs >= 0x00a0 && ucs <= 0x00ff))
        return ucs;

    /* binary search in table */
    while (max >= min) {
	mid = (min + max) / 2;
	if (keysymtab[mid].ucs < ucs)
	    min = mid + 1;
	else if (keysymtab[mid].ucs > ucs)
	    max = mid - 1;
	else {
	    /* found it */
	    return keysymtab[mid].keysym;
	}
    }

    /* no matching keysym value found, return UCS2 with bit set */
    return ucs | 0x01000000;
}

long keysym2ucs(KeySym keysym)
{
    int min = 0;
    int max = sizeof(keysymtab) / sizeof(struct codepair) - 1;
    int mid;

    /* first check for Latin-1 characters (1:1 mapping) */
    if ((keysym >= 0x0020 && keysym <= 0x007e) ||
        (keysym >= 0x00a0 && keysym <= 0x00ff))
        return (long) keysym;

    /* also check for directly encoded 24-bit UCS characters */
    if ((keysym & 0xff000000) == 0x01000000)
	return keysym & 0x00ffffff;

    /* binary search in table */
    while (max >= min) {
	mid = (min + max) / 2;
	if (keysymtab[mid].keysym < keysym)
	    min = mid + 1;
	else if (keysymtab[mid].keysym > keysym)
	    max = mid - 1;
	else {
	    /* found it */
	    return keysymtab[mid].ucs;
	}
    }

    /* no matching Unicode value found */
    return -1;
}

#endif
