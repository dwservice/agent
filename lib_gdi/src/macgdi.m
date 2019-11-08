/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_MAC

#import <Cocoa/Cocoa.h>
#import <AppKit/AppKit.h>

NSAutoreleasePool *pool=NULL;
NSApplication *app=NULL;
NSTimer *timer=NULL;
NSMutableArray *windowList=NULL;
int windowListCnt=0;


const int WINDOW_TYPE_NORMAL=0;
const int WINDOW_TYPE_NORMAL_NOT_RESIZABLE=1;
const int WINDOW_TYPE_DIALOG=100;
const int WINDOW_TYPE_POPUP=200;
const int WINDOW_TYPE_TOOL=300;

typedef void (*CallbackTypeRepaint)(int id, int x,int y,int w, int h);
typedef void (*CallbackTypeKeyboard)(int id, wchar_t* type,wchar_t* c,bool shift,bool ctrl,bool alt,bool meta);
typedef void (*CallbackTypeMouse)(int id, wchar_t* type, int x, int y, int button);
typedef bool (*CallbackTypeWindow)(int id, wchar_t* type);
typedef void (*CallbackTypeTimer)();


CallbackTypeRepaint g_callbackRepaint;
CallbackTypeKeyboard g_callbackKeyboard;
CallbackTypeMouse g_callbackMouse;
CallbackTypeWindow g_callbackWindow;
CallbackTypeTimer g_callbackTimer;


NSString* wchartToNString(wchar_t* inStr){
	if (NSHostByteOrder() == NS_LittleEndian){
		return [[NSString alloc] initWithBytes:inStr length:wcslen(inStr)*sizeof(*inStr) encoding:NSUTF32LittleEndianStringEncoding];
	}else{
		return [[NSString alloc] initWithBytes:inStr length:wcslen(inStr)*sizeof(*inStr) encoding:NSUTF32BigEndianStringEncoding];
	}
}

wchar_t* nStringTowchart(NSString* inStr){
	if (NSHostByteOrder() == NS_LittleEndian){
	    return (wchar_t *)[inStr cStringUsingEncoding:NSUTF32LittleEndianStringEncoding];
	}else{
		return (wchar_t *)[inStr cStringUsingEncoding:NSUTF32BigEndianStringEncoding];
	}
}

void setCallbackRepaint(CallbackTypeRepaint callback){
	g_callbackRepaint = callback;
}

void setCallbackKeyboard(CallbackTypeKeyboard callback){
	g_callbackKeyboard = callback;
}

void setCallbackMouse(CallbackTypeMouse callback){
	g_callbackMouse=callback;
}

void setCallbackWindow(CallbackTypeWindow callback){
	g_callbackWindow=callback;
}

void setCallbackTimer(CallbackTypeTimer callback){
	g_callbackTimer=callback;
}

void fireCallBackRepaint(int id, int x,int y,int w, int h){
	if(g_callbackRepaint)
		g_callbackRepaint(id, x, y, w, h);
}

void fireCallBackKeyboard(int id, wchar_t* type, wchar_t* c,bool bshift){
	if(g_callbackKeyboard)
		g_callbackKeyboard(id, type, c, bshift,false,false,false);
}

void fireCallBackMouse(int id, wchar_t* type, int x, int y, int button){
	if(g_callbackMouse)
		g_callbackMouse(id, type, x, y, button);
}

bool fireCallBackWindow(int id, wchar_t* type){
	if(g_callbackWindow)
		return g_callbackWindow(id,type);
	return true;
}

void fireCallBackTimer(){
	if(g_callbackTimer)
		g_callbackTimer();
}


@interface DWADelegate : NSObject <NSApplicationDelegate> {

}
@end

@implementation DWADelegate


- (void) applicationDidFinishLaunching:(NSNotification *)aNotification{

	//TROVARE SOLUZIONE MIGLIORE
	dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.1 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
	NSImage *imgDock = [[NSImage alloc] initWithContentsOfFile:@"images/logo.icns"];
		if (imgDock != nil){
			if ([imgDock isValid]) {
				[NSApp setApplicationIconImage: imgDock];
			}
			[imgDock release];
		}
	});
}

@end



@interface DWAWindow:NSObject
{
	NSWindow *win;
	NSColor *penColor;
	int wid;
	int x;
	int y;
	int h;
	int w;
	bool boolInit;
	bool boolClipRect;
}
@end

@implementation DWAWindow
-(id)init
{
   self = [super init];
   penColor=[NSColor blackColor];
   boolInit=false;
   boolClipRect=false;
   return self;
}

- (void) setWin : (NSWindow*) p {  win = p; }
- (NSWindow*) win { return win; }

- (void) setPenColor : (NSColor*) p {  penColor = p; }
- (NSColor*) penColor { return penColor; }

- (void) setWid : (int) p {  wid = p; }
- (int) wid { return wid; }

- (void) setX : (int) p {  x = p; }
- (int) x { return x; }

- (void) setY : (int) p {  y = p; }
- (int) y { return y; }

- (void) setW : (int) p {  w = p; }
- (int) w { return w; }

- (void) setH : (int) p {  h = p; }
- (int) h { return h; }

- (void) setBoolInit : (bool) p {  boolInit = p; }
- (bool) boolInit { return boolInit; }

- (void) setBoolClipRect : (bool) p {  boolClipRect = p; }
- (bool) boolClipRect { return boolClipRect; }

@end

DWAWindow* addWindow(NSWindow* win){
	windowListCnt++;
	DWAWindow *ww = [[DWAWindow alloc]init];
	[ww setWin:win];
	[ww setWid:windowListCnt];
	[windowList addObject:ww];
	return ww;
}

DWAWindow* getWindowByID(int id){
	unsigned int i=0;
	for (i=0;i<[windowList count];i++){
		DWAWindow *ww = [windowList objectAtIndex:i];
		if ([ww wid]==id){
			return ww;
		}
	}
	return NULL;
}

void removeWindowByID(int id){
	unsigned int i=0;
	for (i=0;i<[windowList count];i++){
		DWAWindow *ww = [windowList objectAtIndex:i];
		if ([ww wid]==id){
			[windowList removeObject:ww];
			return;
		}
	}

}

@interface GView : NSView <NSWindowDelegate> {
	int wid;
	int h;
	int w;
	bool bfocus;
}
-(void)drawRect:(NSRect)rect;
@end

@implementation GView
-(id)init
{
   self = [super init];
   bfocus=false;
   return self;
}

- (void) setWid : (int) p {  wid = p; }
- (int) wid { return wid; }

- (void) setW : (int) p {  w = p; }
- (int) w { return w; }

- (void) setH : (int) p {  h = p; }
- (int) h { return h; }

-(void)drawRect:(NSRect)rect {
	[[NSColor whiteColor] set];
	NSRectFill( [self bounds] );
	fireCallBackRepaint(wid,[self bounds].origin.x,[self bounds].origin.y,[self bounds].size.width,[self bounds].size.height);
}

- (BOOL)acceptsFirstResponder {
    return YES;
}


- (void)keyDown:(NSEvent *)theEvent {
	[self interpretKeyEvents:[NSArray arrayWithObject:theEvent]];
	//NSLog(@"keyDown");
}

- (void)insertText:(id)string{
    [super insertText:string];
    int n = [string length];
    int i=0;
    for (i=0;i<n;i++){
    	NSString* c = [string substringWithRange:NSMakeRange(i, 1)];
    	//NSLog(c);
    	wchar_t* buffer=nStringTowchart(c);
    	fireCallBackKeyboard(wid,L"CHAR",buffer,false);
    }
}

-(IBAction)insertTab:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"TAB",false);
}

-(IBAction)insertBacktab:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"TAB",true);
}

-(IBAction)deleteBackward:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"BACKSPACE",false);
}

-(IBAction)deleteForward:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"DELETE",false);
}

-(IBAction)moveLeft:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"LEFT",false);
}

-(IBAction)moveLeftAndModifySelection:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"LEFT",true);
}

-(IBAction)moveRight:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"RIGHT",false);
}

-(IBAction)moveRightAndModifySelection:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"RIGHT",true);
}

-(IBAction)moveToBeginningOfLine:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"HOME",false);
}

-(IBAction)moveToBeginningOfLineAndModifySelection:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"HOME",true);
}

-(IBAction)moveToEndOfLine:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"END",false);
}

-(IBAction)moveToEndOfLineAndModifySelection:(id)sender{
	fireCallBackKeyboard(wid,L"KEY",L"END",true);
}

- (void)mouseMoved:(NSEvent *)theEvent {
	NSPoint p = [theEvent locationInWindow];
	float x=(int)p.x;
	float y=(int)(h-p.y);
	if ((x>0) && (y>0) && (x<=w) && (y<=h)) {
		fireCallBackMouse(wid,L"MOVE",x,y,0);
		//NSLog(@"mouseMove x: %f y: %f",x,y);
	}
}

- (void)mouseDown:(NSEvent *)theEvent {
	NSPoint p = [theEvent locationInWindow];
	float x=(int)p.x;
	float y=(int)(h-p.y);
	if ((x>0) && (y>0) && (x<=w) && (y<=h)) {
		fireCallBackMouse(wid,L"BUTTON_DOWN",x,y,1);
		//NSLog(@"mouseDown x: %f y: %f",x,y);
	}
}

- (void)mouseUp:(NSEvent *)theEvent {
	NSPoint p = [theEvent locationInWindow];
	float x=(int)p.x;
	float y=(int)(h-p.y);
	if ((x>0) && (y>0) && (x<=w) && (y<=h)) {
		fireCallBackMouse(wid,L"BUTTON_UP",x,y,1);
		//NSLog(@"mouseUp x: %f y: %f",x,y);
	}
}

- (BOOL)windowShouldClose:(NSNotification *)note {
	return fireCallBackWindow(wid,L"ONCLOSE");
}

- (void)windowWillClose:(NSNotification *)note {
	removeWindowByID(wid);
	if ([windowList count]==0){
		[app stop:self];
		[app terminate: self];
	}
}

- (BOOL)canBecomeKeyWindow {
    return YES;
}

- (BOOL)canBecomeMainWindow {
    return YES;
}

-(void)windowDidBecomeMain:(NSNotification *)note {
	[self gotFocus];
}

-(void)windowDidBecomeKey:(NSNotification *)note {
	[self gotFocus];
}

-(void)windowDidResignMain:(NSNotification *)note {
	[self lostFocus];
}

-(void)windowDidResignKey:(NSNotification *)note {
	[self lostFocus];
}

-(void)gotFocus{
	dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.05 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
		if (!bfocus){
			//NSLog(@"GOT FOCUS %d",wid);
			fireCallBackWindow(wid,L"ACTIVE");
		}
		bfocus=true;
	});
}

-(void)lostFocus{
	dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.05 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
		if (bfocus){
			//NSLog(@"LOST FOCUS %d",wid);
			fireCallBackWindow(wid,L"INACTIVE");
		}
		bfocus=false;
	});
}
@end


@interface DWATimer:NSObject{

}
@end

@implementation DWATimer
-(id)init
{
   return self;
}

-(void)onTick:(NSTimer*)timer{
	fireCallBackTimer();
}
@end


void loop(){
	[app run];
	[pool release];
}

int newWindow(int tp,int x, int y, int w, int h, wchar_t* iconPath){
	if (app==NULL){
		pool = [NSAutoreleasePool new];

		//[NSApp setPoolProtected:NO];

		windowList = [[NSMutableArray alloc] init];

		//[NSApp setDelegate: [DWADelegate new]];


		app = [NSApplication sharedApplication];
		[NSApp setDelegate:[[DWADelegate alloc] init]];

		timer = [NSTimer scheduledTimerWithTimeInterval: 0.1
				 target: [DWATimer new]
				 selector: @selector(onTick:)
				 userInfo: nil
				 repeats: YES];

		[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
		[NSApp activateIgnoringOtherApps:YES];


		id menubar = [[NSMenu new] autorelease];
		id appMenuItem = [[NSMenuItem new] autorelease];
		[menubar addItem:appMenuItem];
		[NSApp setMainMenu:menubar];
		id appMenu = [[NSMenu new] autorelease];
		//id appName = [[NSProcessInfo processInfo] processName];
		//id quitTitle = [@"Quit " stringByAppendingString:appName];
		id quitTitle = [@"Quit " stringByAppendingString:@""];
		id quitMenuItem = [[[NSMenuItem alloc] initWithTitle:quitTitle
		action:@selector(terminate:) keyEquivalent:@"q"] autorelease];
		[appMenu addItem:quitMenuItem];
		[appMenuItem setSubmenu:appMenu];



		/*dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.5 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
			NSImage *imgDock = [[NSImage alloc] initWithContentsOfFile:@"/Library/DWAgent/images/logo.icns"];
									if (imgDock != nil){
										if ([imgDock isValid]) {
											NSLog(@"OK21");
											[NSApp setApplicationIconImage: imgDock];
										}else{
											NSLog(@"ERRORE2");
										}
										[imgDock release];
									}else{
										NSLog(@"ERRORE");

									}
			});*/
/*
		NSImage *imgDock = [[NSImage alloc] initWithContentsOfFile:@"/Library/DWAgent/images/logo.icns"];
		//NSImage *imgDock = [NSImage imageNamed: @"DWAgent"];
						if (imgDock != nil){
							if ([imgDock isValid]) {
								NSLog(@"OK21");
								[NSApp setApplicationIconImage: imgDock];
							}else{
								NSLog(@"ERRORE2");
							}
							[imgDock release];
						}else{
							NSLog(@"ERRORE");
						}*/

	}
	NSRect e = [[NSScreen mainScreen] frame];
	NSRect frame = NSMakeRect(x, e.size.height-h-y+50, w, h);  //50 centra meglio

	int sm=NSTitledWindowMask | NSClosableWindowMask | NSMiniaturizableWindowMask;
	if (tp==WINDOW_TYPE_TOOL){
		sm=NSTitledWindowMask;
	}else if (tp==WINDOW_TYPE_DIALOG){
		sm=NSTitledWindowMask;
	}

	NSWindow *window = [[NSWindow alloc]
		initWithContentRect:frame
				  styleMask:sm
					backing:NSBackingStoreBuffered
					  defer:false];


	DWAWindow* ww=addWindow(window);
	[ww setX:x];
	[ww setY:y];
	[ww setW:w];
	[ww setH:h];
	return [ww wid];
}

void destroyWindow(int id){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		NSWindow *window = [dwa win];
		[window close];
	}
}

void setTitle(int id, wchar_t* title){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		NSWindow *window = [dwa win];
		NSString* nsTitle = wchartToNString(title);
		[window setTitle:nsTitle];
	}
}


void getScreenSize(int* size){
	NSRect e = [[NSScreen mainScreen] frame];
	size[0]=e.size.width;
	size[1]=e.size.height;
}

void show(int id,int mode){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		NSWindow *window = [dwa win];
		NSRect frame = [window frame];
		//[[window windowController] setShouldCascadeWindows:true];
		GView *view = [window contentView];
		if (!dwa.boolInit){
			dwa.boolInit=true;
			view = [[[GView alloc] initWithFrame:frame] autorelease];
			[view setWid:id];
			[view setW:[dwa w]];
			[view setH:[dwa h]];
			[window setContentView:view];
			[window setDelegate:view];
			[window setAcceptsMouseMovedEvents:YES];
			[window makeKeyAndOrderFront:nil];
			[window setOrderedIndex:0];
		}else{
			[window showWindow:view];
		}
	}
}

void hide(int id){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		NSWindow *window = [dwa win];
		[window orderOut:[window contentView]];

	}
}

void toFront(int id){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		NSWindow *window = [dwa win];
		GView *view = [window contentView];
		[window orderFront:view];
		[window makeKeyAndOrderFront:nil];
		//[view gotFocus];
	}
}

void penColor(int id, int r, int g, int b){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		[dwa setPenColor:[NSColor colorWithCalibratedRed:(r/255.0f) green:(g/255.0f) blue:(b/255.0f) alpha:1.0]];
	}
}

void penWidth(int id, int w){

}

void drawLine(int id, int x1,int y1,int x2,int y2){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		[[NSGraphicsContext currentContext] setShouldAntialias: NO];
		NSWindow *window = [dwa win];
		[[dwa penColor] set];
		NSPoint p1 = NSMakePoint(x1,dwa.h-y1-1);
		NSPoint p2 = NSMakePoint(x2,dwa.h-y2-1);
		NSBezierPath* bp = [NSBezierPath bezierPath];
		[bp setLineWidth:1];
		[bp moveToPoint:p1];
		[bp lineToPoint:p2];
		[bp stroke];
	}
}

void drawEllipse(int id, int x, int y, int w,int h){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		[[NSGraphicsContext currentContext] setShouldAntialias: NO];
		[[dwa penColor] setStroke];
		NSRect rect = NSMakeRect(x, dwa.h-h-y, w, h);
		NSBezierPath* circlePath = [NSBezierPath bezierPath];
		[circlePath appendBezierPathWithOvalInRect: rect];
		[circlePath stroke];
	}
}

void fillEllipse(int id, int x, int y, int w,int h){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		[[NSGraphicsContext currentContext] setShouldAntialias: NO];
		[[dwa penColor] setStroke];
		[[dwa penColor] setFill];
		NSRect rect = NSMakeRect(x, dwa.h-h-y, w, h);
		NSBezierPath* circlePath = [NSBezierPath bezierPath];
		[circlePath appendBezierPathWithOvalInRect: rect];
		[circlePath stroke];
		[circlePath fill];
	}
}


int getTextHeight(int id){
	NSFont* fnt = [NSFont menuBarFontOfSize:0];
	return fnt.xHeight+8;
}

int getTextWidth(int id,wchar_t* str){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		[[NSGraphicsContext currentContext] setShouldAntialias: YES];
		NSFont* fnt = [NSFont menuBarFontOfSize:0];
		NSDictionary *attributes = [NSDictionary dictionaryWithObjectsAndKeys:fnt, NSFontAttributeName,[dwa penColor], NSForegroundColorAttributeName, nil];
		NSString* nsStr = wchartToNString(str);
		NSAttributedString * currentText=[[NSAttributedString alloc] initWithString:nsStr attributes: attributes];
		NSSize attrSize = [currentText size];
		return attrSize.width;
	}
	return 0;
}

void drawText(int id, wchar_t* str, int x, int y){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		[[NSGraphicsContext currentContext] setShouldAntialias: YES];
		NSWindow *window = [dwa win];
		NSFont* fnt = [NSFont menuBarFontOfSize:0];
		NSDictionary *attributes = [NSDictionary dictionaryWithObjectsAndKeys:fnt, NSFontAttributeName,[dwa penColor], NSForegroundColorAttributeName, nil];
		NSString* nsStr = wchartToNString(str);
		NSAttributedString * currentText=[[NSAttributedString alloc] initWithString:nsStr attributes: attributes];
		[currentText drawAtPoint:NSMakePoint(x, dwa.h-(y+fnt.ascender+2))];
	}
}

void fillRectangle(int id, int x, int y, int w,int h){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		//NSWindow *window = [dwa win];
		[[NSGraphicsContext currentContext] setShouldAntialias: NO];
		[[dwa penColor] set];
		NSRect rec = NSMakeRect(x, dwa.h-h-y, w, h);
		NSRectFill(rec);
	}
}

void repaint(int id, int x, int y, int w, int h){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		NSWindow *window = [dwa win];
		NSRect rec = NSMakeRect(x, dwa.h-h-y, w, h);
		[[window contentView] setNeedsDisplayInRect:rec];
		//[[window contentView] setNeedsDisplay:YES];
	}
}

void clipRectangle(int id, int x, int y, int w, int h){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		if ([dwa boolClipRect]==true){
			[[NSGraphicsContext currentContext] restoreGraphicsState];
			[dwa setBoolClipRect:false];
		}
		[[NSGraphicsContext currentContext] saveGraphicsState];
		NSRectClip(NSMakeRect(x, dwa.h-h-y, w, h));
		[dwa setBoolClipRect:true];
	}
}

void clearClipRectangle(int id){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		if ([dwa boolClipRect]==true){
			[[NSGraphicsContext currentContext] restoreGraphicsState];
			[dwa setBoolClipRect:false];
		}
	}
}

int main(int argc, const char *argv[]) {

	int id = newWindow(WINDOW_TYPE_NORMAL_NOT_RESIZABLE,0,0,400,300, NULL);

	setTitle(id,L"Prova");
	//createNotifyIcon(id,L"",L"Tooltip");
	show(id,0);

	loop();

	return( EXIT_SUCCESS );
}

void createNotifyIcon(int id,wchar_t* iconPath,wchar_t* toolTip){
}

void setClipboardText(wchar_t* str){

}

wchar_t* getClipboardText(){
	return NULL;
}

void updateNotifyIcon(int id,wchar_t* iconPath,wchar_t* toolTip){
}

void destroyNotifyIcon(int id){
}

void getMousePosition(int* pos){
}

#endif
