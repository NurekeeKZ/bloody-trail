"""Local face-anchored upper-body optical flow; not emotion/lie recognition.
ROI includes approximate shoulders and arms. Background/global light changes are
rejected where detectable; this is an imperfect motion proxy, not pose estimation.
"""
class MotionDetector:
    def __init__(self):
        import cv2
        self.cv=cv2;self.face=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
        self.previous=None;self.previous_box=None
    def process(self,frame,dt):
        gray=self.cv.cvtColor(frame,self.cv.COLOR_BGR2GRAY)
        boxes=self.face.detectMultiScale(self.cv.equalizeHist(gray),1.15,5,minSize=(60,60))
        box=tuple(map(int,boxes[0])) if len(boxes)==1 else None
        return self.measure(gray,box,dt)
    def measure(self,gray,box,dt):
        import numpy as np
        result={'present':box is not None,'reliable':False,'motion':0.,'lighting':False}
        previous=self.previous;old_box=self.previous_box
        self.previous=gray.copy();self.previous_box=box
        if box is None or old_box is None or previous is None or gray.shape!=previous.shape:return result
        change=float(np.median(gray.astype(float)-previous.astype(float)))
        if abs(change)>18:
            result['lighting']=True;return result
        x,y,w,h=old_box;mask=np.zeros_like(gray)
        left=max(0,int(x-w));right=min(gray.shape[1],int(x+2*w))
        top=max(0,y);bottom=min(gray.shape[0],int(y+3.4*h));mask[top:bottom,left:right]=255
        points=self.cv.goodFeaturesToTrack(previous,100,.02,8,mask=mask)
        if points is None or len(points)<8:return result
        adjusted=np.clip(gray.astype(float)-change,0,255).astype('uint8')
        moved,status,_=self.cv.calcOpticalFlowPyrLK(previous,adjusted,points,None,winSize=(21,21),maxLevel=3)
        if moved is None:return result
        valid=status.flatten()==1
        if valid.sum()<8:return result
        distances=np.linalg.norm(moved[valid]-points[valid],axis=2).flatten()
        # Reject whole-frame camera shake, rather than punish a moving camera/background.
        outside=255-mask
        bg=self.cv.goodFeaturesToTrack(previous,60,.03,10,mask=outside)
        if bg is not None and len(bg)>=8:
            bg_next,bg_status,_=self.cv.calcOpticalFlowPyrLK(previous,adjusted,bg,None)
            if bg_next is not None and (bg_status==1).sum()>=8:
                displacement=np.linalg.norm((bg_next-bg).reshape(-1,2)[bg_status.flatten()==1],axis=1)
                if float(np.median(displacement))>2.5:return result
        result['reliable']=True
        result['motion']=float(np.percentile(distances,75))/(max(w,1)*max(.03,min(.3,dt)))
        return result
