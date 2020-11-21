/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#import <Cocoa/Cocoa.h>
#import <AppKit/AppKit.h>



NSAutoreleasePool *pool=NULL;
NSApplication *app=NULL;
NSTimer *timer=NULL;
NSWindow *window=NULL;
NSString *errclose = nil;
BOOL bclose = NO;
int currentPerc=0;
int height=40;
int width=250;

@interface DWADelegate : NSObject <NSApplicationDelegate> {

}
@end

@implementation DWADelegate


- (void) applicationDidFinishLaunching:(NSNotification *)aNotification{

}
@end

@interface IGView : NSView <NSWindowDelegate> {
}
-(void)drawRect:(NSRect)rect;
@end

@implementation IGView
-(id)init
{
   self = [super init];
   return self;
}

-(void)drawRect:(NSRect)rect {
	[[NSGraphicsContext currentContext] setShouldAntialias: NO];
	[[NSColor whiteColor] set];
	NSRectFill( [self bounds] );

	int rx=20;
	int ry=15;
	int rw=width-(2*rx);
	int rh=8;

	[[NSColor grayColor] set];
	NSBezierPath* bp = [NSBezierPath bezierPath];
	[bp setLineWidth:1];
	[bp moveToPoint:NSMakePoint(rx,height-rh-ry-1)];
	[bp lineToPoint:NSMakePoint(rx+rw,height-rh-ry-1)];
	[bp lineToPoint:NSMakePoint(rx+rw,height-ry-1)];
	[bp lineToPoint:NSMakePoint(rx,height-ry-1)];
	[bp closePath];
	[bp stroke];

	if (currentPerc>0){
		int pw=(int)((float)(rw*currentPerc)/(float)100);
		[[NSColor colorWithCalibratedRed:(114/255.0f) green:(159/255.0f) blue:(207/255.0f) alpha:1.0] set];
		NSRect rec = NSMakeRect(rx, height-rh-ry, pw, rh);
		NSRectFill(rec);
	}
}

- (void)windowWillClose:(NSNotification *)note {
	[app stop:self];
	[app terminate: self];
}
@end


@interface ITimer:NSObject{

}
@end

@implementation ITimer
-(id)init
{
   return self;
}

-(void)onTick:(NSTimer*)timer{
	if (bclose==YES){
		if (errclose!=nil){
			NSAlert *alert = [[[NSAlert alloc] init] autorelease];
			[alert setMessageText:errclose];
			[alert runModal];
		}
		[window close];
	}
}
@end

@interface TDRunInstall:NSObject {
	NSThread *_thread;
}
@end

@implementation TDRunInstall {

}

- (NSThread *) thread
{
    if (!_thread) {
        _thread = [[NSThread alloc]
                  initWithTarget:self
                  selector:@selector(run:)
                  object:nil];
    }
    return _thread;
}

- (void)start {
	[self.thread start];
}


- (void)removeFileRunAsAdminInstall:(NSString*)basepth {
	BOOL exists = [[NSFileManager defaultManager] fileExistsAtPath:[basepth stringByAppendingString:@"/runasadmin.install"]];
	if (exists==YES){
		NSError *error = [NSError new];
		[[NSFileManager defaultManager] removeItemAtPath:[basepth stringByAppendingString:@"/runasadmin.install"] error:&error];
		[error release];
	}
}

- (BOOL)existsFileRunAsAdminInstall:(NSString*)basepth {
	BOOL exists = [[NSFileManager defaultManager] fileExistsAtPath:[basepth stringByAppendingString:@"/runasadmin.install"]];
	return exists;
}

- (void)extractData:(NSNotification *)notif {
    NSFileHandle *fh = [notif object];
    NSData *data = [fh availableData];
    if (data.length > 0) { // if data is found, re-register for more data (and print)
        [fh waitForDataInBackgroundAndNotify];
        NSString *str = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
        NSRange r = [str rangeOfString:@"%"];
        if (r.location!=NSNotFound){
        	if (r.location>=3){
        		NSRange rsub = NSMakeRange(r.location-3,3);
        		NSString *rstr = [str substringWithRange:rsub];
        		int perc = [rstr intValue];
        		if (perc>currentPerc){
        			currentPerc=perc;
        			NSRect rec = NSMakeRect(0, 0, width, height);
        			[[window contentView] setNeedsDisplayInRect:rec];
        		}
        	}
        }
    }
}

- (void)run:(id)sender {
	NSString *exepth = [[[NSProcessInfo processInfo] arguments] objectAtIndex:0];
	NSRange r = [exepth rangeOfString:@"/" options:NSBackwardsSearch];
	if (r.location!=NSNotFound){
		NSRange rsub = NSMakeRange(0,r.location);
		exepth=[exepth substringWithRange:rsub];
		//errclose=[exepth copy];
	}else{
		errclose=@"Error detect executable path.";
	}
	NSString *dirString = @"dwagentinstall";
	NSDateFormatter *date = [[NSDateFormatter alloc] init];
	[date setDateFormat:@"yyyyMMddHHmmss"];
	NSString *dateString = [date stringFromDate:[NSDate date]];
	NSString *basepth = [NSTemporaryDirectory() stringByAppendingPathComponent:[dirString stringByAppendingString:dateString]];

	if (errclose==nil){
		//Crea Directory
		if ([[NSFileManager defaultManager] fileExistsAtPath:basepth]==NO){
			NSError *errormkdir = [NSError new];
			if(![[NSFileManager defaultManager] createDirectoryAtPath:basepth withIntermediateDirectories:YES attributes:nil error:&errormkdir]){
				errclose=@"Error create temp directory.";
			}
			[errormkdir release];
		}
	}

	if (errclose==nil){
		//Estrae i file
		NSString *extractpath=[exepth stringByAppendingString:@"/extract"];
		if (([[NSFileManager defaultManager] fileExistsAtPath:extractpath]==YES) && ([[NSFileManager defaultManager] fileExistsAtPath:[extractpath stringByAppendingString:@".7z"]]==YES)){
			NSTask *taskextract = [[NSTask alloc] init];
			[taskextract setLaunchPath: extractpath];
			[taskextract setArguments:[NSArray arrayWithObjects: @"-y", nil]];
			[taskextract setCurrentDirectoryPath:basepth];

			NSPipe *p = [NSPipe pipe];
			[taskextract setStandardOutput:p];
			NSFileHandle *fh = [p fileHandleForReading];
			[fh waitForDataInBackgroundAndNotify];

			[[NSNotificationCenter defaultCenter] addObserver:self selector:@selector(extractData:) name:NSFileHandleDataAvailableNotification object:fh];

			[taskextract launch];
			[taskextract waitUntilExit];
			if ([taskextract terminationStatus] != 0){
				errclose=@"Error decompress file.";
			}
		}else{
			errclose=@"Error missing extract.";
		}
	}

	if (errclose==nil){
		//Esgue installer
		NSString *installpath=[exepth stringByAppendingString:@"/install"];
		if ([[NSFileManager defaultManager] fileExistsAtPath:installpath]==YES){
			//Fix High Sierra
			if ([[NSFileManager defaultManager] fileExistsAtPath:@"/usr/lib/libz.1.2.8.dylib"]==YES){
				NSString *libzpath=[basepth stringByAppendingString:@"/runtime/lib/libz.1.2.8.dylib"];
				NSError *appError = nil;
				[[NSFileManager defaultManager] removeItemAtPath:libzpath error:&appError];
			    [[NSFileManager defaultManager] copyItemAtPath:@"/usr/lib/libz.1.2.8.dylib" toPath:libzpath error:&appError];
			}
			[NSThread sleepForTimeInterval:0.25f];
			[window orderOut:[window contentView]]; //Nasconde finestra

			BOOL runAsAdmin=NO;
			while(true){
				[self removeFileRunAsAdminInstall:basepth];

				NSTask *taskrun = [[NSTask alloc] init];
				[taskrun setLaunchPath: installpath];
				if (runAsAdmin==YES){
					[taskrun setArguments:[NSArray arrayWithObjects: basepth, @"Y", nil]];
				}else{
					[taskrun setArguments:[NSArray arrayWithObjects: basepth, @"N", nil]];
				}
				[taskrun setCurrentDirectoryPath:basepth];
				[taskrun launch];
				[taskrun waitUntilExit];

				if ([taskrun terminationStatus] == 0){
					if ((!runAsAdmin) && ([self existsFileRunAsAdminInstall:basepth])){
						runAsAdmin=YES;
					}else{
						break;
					}
				}else{
					if (runAsAdmin){
						runAsAdmin=false;
					}else{
						errclose=@"Error run installer.";
						break;
					}
				}
				[taskrun release];
			}
		}else{
			errclose=@"Error missing install.";
		}
	}

	if ([[NSFileManager defaultManager] fileExistsAtPath:basepth]==YES){
		NSError *errordeldir = [NSError new];
		[[NSFileManager defaultManager] removeItemAtPath:basepth error:&errordeldir];
		[errordeldir release];
	}
	bclose=YES;

}
@end

void loop(){
	[app run];
	[pool release];
}

int main(int argc, const char *argv[]) {

	pool = [NSAutoreleasePool new];
	//[NSApp setPoolProtected:NO];
	//[NSApp setDelegate: [DWADelegate new]];
	app = [NSApplication sharedApplication];
	[NSApp setDelegate:[[DWADelegate alloc] init]];

	timer = [NSTimer scheduledTimerWithTimeInterval: 0.5
					 target: [ITimer new]
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
	NSRect e = [[NSScreen mainScreen] frame];
	int h=height;
	int w=width;
	int x=(e.size.width/2)-(w/2);
	int y=(e.size.height/2)-(h/2);
	NSRect frame = NSMakeRect(x, e.size.height-h-y+50, w, h); //50 centra meglio
	window = [[NSWindow alloc]
		initWithContentRect:frame
				  styleMask:NSTitledWindowMask
					backing:NSBackingStoreBuffered
					  defer:false];


	//TITOLO
	[window setTitle:@"DWAgent"];

	//SHOW
	IGView *view = [window contentView];
	view = [[[IGView alloc] initWithFrame:frame] autorelease];
	[window setContentView:view];
	[window setDelegate:view];
	[window setAcceptsMouseMovedEvents:YES];
	[window makeKeyAndOrderFront:nil];
	[window setOrderedIndex:0];

	//THREAD
	TDRunInstall *ri = [[TDRunInstall alloc] init];
	[ri start];

	loop();

	return( EXIT_SUCCESS );
}

