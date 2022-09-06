#if defined OS_MAC

#ifndef MACOBJC_H_
#define MACOBJC_H_

int macobjcGetClipboardText(wchar_t** wText);
void macobjcSetClipboardText(wchar_t* wText);

#endif /* MACOBJC_H_ */
#endif
