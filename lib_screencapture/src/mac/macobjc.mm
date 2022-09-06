#if defined OS_MAC

#include <AppKit/AppKit.h>
#include <wchar.h>

int macobjcGetClipboardText(wchar_t** wText){
	NSPasteboard* pasteboard = [NSPasteboard generalPasteboard];
	NSString* string = [pasteboard stringForType:NSPasteboardTypeString];
	int reqsize = [string lengthOfBytesUsingEncoding:NSUTF8StringEncoding]+1;
	if (reqsize>1){
		char* buf = (char*)malloc(reqsize);
		memcpy(buf, [string UTF8String], reqsize);
		*wText = (wchar_t*)malloc((reqsize+1) * sizeof(wchar_t));
		mbstowcs(*wText, (char*)buf, reqsize+1);
		free(buf);
		return [string length];
	}else{
		return 0;
	}
}

void macobjcSetClipboardText(wchar_t* wText){
	size_t len = wcstombs(NULL, wText, 0);
	char* buf = (char*)malloc(((len)+1) * sizeof(char));
	wcstombs(buf, wText, len+1);
	NSString* string = [[NSString alloc] initWithBytes:(void*)buf
	                                     length:len
	                                     encoding:NSUTF8StringEncoding];
	free(buf);
	NSPasteboard* pasteboard = [NSPasteboard generalPasteboard];
	[pasteboard clearContents];
	[pasteboard setString:string forType:NSPasteboardTypeString];
}

#endif
