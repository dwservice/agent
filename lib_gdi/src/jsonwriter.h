/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include <string>
#include <sstream>

using namespace std;

#ifndef JSONWRITER_H_
#define JSONWRITER_H_

class JSONWriter{
public:
	JSONWriter();
	void beginObject();
	void endObject();
	void beginArray();
	void endArray();
	void addString(wstring name, wstring value);
	void addNumber(wstring name,int value);
	void addNumber(wstring name,long value);
	void addNumber(wstring name,unsigned long value);
	void addNumber(wstring name,unsigned long long value);
	void addBoolean(wstring name, bool value);
	void clear();
	int length();
	wstring getString();


private:
	wstring data;
	void addProp(wstring name);
};

#endif /* JSONWRITER_H_ */
